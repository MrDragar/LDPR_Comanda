import logging
from sqlalchemy import select, func
from src.domain.entities.hill import HillVote
from src.domain.entities.petition import Petition, PetitionStatus
from src.domain.entities.user import Sources
from src.domain.interfaces import IHillRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.hill import HillVoteORM
from src.infrastructure.models.petition import PetitionORM

logger = logging.getLogger(__name__)


class HillRepository(IHillRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_pair_for_user(self, user_id: int, source: Sources) -> tuple[
                                                                            Petition, Petition] | None:
        session = self.__uow.get_session()

        # 1. Подзапрос: находим ID петиций, против которых пользователь голосовал.
        # Петиция считается "отклоненной", если она участвовала в голосовании, но НЕ стала winner_id.
        # Используем UNION, чтобы проверить оба столбца (left и right).
        left_rejected = select(HillVoteORM.petition_left_id).where(
            HillVoteORM.user_id == user_id,
            HillVoteORM.user_source == source,
            HillVoteORM.winner_id != HillVoteORM.petition_left_id
        )

        right_rejected = select(HillVoteORM.petition_right_id).where(
            HillVoteORM.user_id == user_id,
            HillVoteORM.user_source == source,
            HillVoteORM.winner_id != HillVoteORM.petition_right_id
        )

        rejected_ids_subq = left_rejected.union(right_rejected)

        # 2. Основной запрос: берем 2 случайные петиции, которых нет в списке отклоненных.
        # Все это компилируется в ОДИН SQL запрос с конструкцией WHERE id NOT IN (SELECT ...)
        stmt = (
            select(PetitionORM)
            .where(
                PetitionORM.status.in_([
                    PetitionStatus.PUBLISHED,
                    PetitionStatus.IN_PROGRESS,
                    PetitionStatus.COMPLETED
                ]),
                PetitionORM.id.notin_(rejected_ids_subq)
            )
            .order_by(func.random())  # Случайная сортировка (RAND() в MySQL, RANDOM() в SQLite/PG)
            .limit(2)
        )

        result = await session.execute(stmt)
        candidates = result.scalars().all()

        # Если в пуле осталось меньше 2 петиций, битву проводить не из чего
        if len(candidates) < 2:
            return None

        return self._to_domain(candidates[0]), self._to_domain(candidates[1])

    async def save_vote(self, vote: HillVote) -> HillVote:
        session = self.__uow.get_session()
        orm = HillVoteORM(
            user_id=vote.user_id, user_source=vote.user_source,
            petition_left_id=vote.petition_left_id, petition_right_id=vote.petition_right_id,
            winner_id=vote.winner_id
        )
        session.add(orm)
        await session.flush()
        vote.id = orm.id
        return vote

    async def get_user_votes_count(self, user_id: int, source: Sources) -> int:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(HillVoteORM).where(
            HillVoteORM.user_id == user_id,
            HillVoteORM.user_source == source
        )
        return await session.scalar(stmt) or 0

    def _to_domain(self, orm: PetitionORM) -> Petition:
        return Petition(
            id=orm.id, title=orm.title, description=orm.description, region=orm.region,
            scope=orm.scope, image_url=orm.image_url, author_id=orm.author_id,
            author_source=orm.author_source.value, author_name=orm.author_name,
            support_count=orm.support_count, share_count=orm.share_count,
            view_count=orm.view_count, status=orm.status, candidate_id=orm.candidate_id,
            candidate_name=orm.candidate_name, candidate_progress=orm.candidate_progress,
            candidate_result=orm.candidate_result,
            candidate_result_image=orm.candidate_result_image,
            created_at=orm.created_at
        )
