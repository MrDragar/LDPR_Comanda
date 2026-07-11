import logging
from sqlalchemy import select, func, update
from src.domain.entities.petition import Petition, PetitionStatus, PetitionScope
from src.domain.entities.user import Sources
from src.domain.interfaces import IPetitionRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.petition import PetitionORM, PetitionSupportORM, PetitionSkipORM

logger = logging.getLogger(__name__)


class PetitionRepository(IPetitionRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def create(self, petition: Petition) -> Petition:
        session = self.__uow.get_session()
        orm = PetitionORM(
            title=petition.title, description=petition.description, region=petition.region,
            scope=petition.scope, image_url=petition.image_url, author_id=petition.author_id,
            author_source=petition.author_source, author_name=petition.author_name,
            status=petition.status
        )
        session.add(orm)
        await session.flush()
        petition.id = orm.id
        return petition

    async def get_by_id(self, petition_id: int) -> Petition | None:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).where(PetitionORM.id == petition_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return self._to_domain(orm)

    async def get_feed(self, scope: str | None, region: str | None, limit: int,
                       user_id: int | None = None, source: Sources | None = None) -> list[Petition]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).where(PetitionORM.status == PetitionStatus.PUBLISHED)
        if scope: stmt = stmt.where(PetitionORM.scope == scope)
        if region: stmt = stmt.where(PetitionORM.region == region)

        if user_id and source:
            skipped_ids = await self.get_skipped_ids(user_id, source)
            if skipped_ids:
                stmt = stmt.where(PetitionORM.id.notin_(skipped_ids))

        stmt = stmt.order_by(PetitionORM.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()]

    async def get_all(self, scope: str | None, status: str | None, region: str | None, page: int,
                      limit: int) -> tuple[list[Petition], int]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM)
        if scope: stmt = stmt.where(PetitionORM.scope == scope)
        if status: stmt = stmt.where(PetitionORM.status == status)
        if region: stmt = stmt.where(PetitionORM.region == region)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0

        stmt = stmt.order_by(PetitionORM.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def get_my(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[
        list[Petition], int]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).where(PetitionORM.author_id == user_id,
                                         PetitionORM.author_source == source)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(PetitionORM.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def get_supported(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[
        list[Petition], int]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).join(
            PetitionSupportORM, PetitionSupportORM.petition_id == PetitionORM.id
        ).where(
            PetitionSupportORM.user_id == user_id,
            PetitionSupportORM.user_source == source
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(PetitionSupportORM.created_at.desc()).offset((page - 1) * limit).limit(
            limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def support(self, petition_id: int, user_id: int, source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(PetitionSupportORM).where(
            PetitionSupportORM.petition_id == petition_id,
            PetitionSupportORM.user_id == user_id,
            PetitionSupportORM.user_source == source
        )
        existing = await session.scalar(stmt)
        if existing: return False

        support_orm = PetitionSupportORM(petition_id=petition_id, user_id=user_id,
                                         user_source=source)
        session.add(support_orm)

        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(
                support_count=PetitionORM.support_count + 1)
        )
        await session.flush()
        return True

    async def is_supported(self, petition_id: int, user_id: int, source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(PetitionSupportORM).where(
            PetitionSupportORM.petition_id == petition_id,
            PetitionSupportORM.user_id == user_id,
            PetitionSupportORM.user_source == source
        )
        return (await session.scalar(stmt) or 0) > 0

    async def increment_share(self, petition_id: int) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(
                share_count=PetitionORM.share_count + 1)
        )
        await session.flush()

    async def increment_view(self, petition_id: int) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(
                view_count=PetitionORM.view_count + 1)
        )
        await session.flush()

    async def update_status(self, petition_id: int, status: PetitionStatus) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(status=status)
        )
        await session.flush()

    async def get_available_for_candidate(self, region: str, page: int, limit: int) -> tuple[list[Petition], int]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).where(
            PetitionORM.status == PetitionStatus.PUBLISHED,
            PetitionORM.scope == PetitionScope.REGION,
            PetitionORM.region == region,
            PetitionORM.candidate_id.is_(None)
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(PetitionORM.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def get_by_candidate(self, candidate_id: int, status: str, page: int, limit: int) -> tuple[list[Petition], int]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM).where(PetitionORM.candidate_id == candidate_id)
        if status:
            stmt = stmt.where(PetitionORM.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(PetitionORM.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def take_petition(self, petition_id: int, candidate_id: int, candidate_name: str, initial_comment: str) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(
                PetitionORM.id == petition_id,
                PetitionORM.candidate_id.is_(None),
                PetitionORM.status == PetitionStatus.PUBLISHED
            ).values(
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                status=PetitionStatus.IN_PROGRESS,
                candidate_progress=initial_comment
            )
        )
        await session.flush()

    async def update_progress(self, petition_id: int, comment: str) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(candidate_progress=comment)
        )
        await session.flush()

    async def complete_petition(self, petition_id: int, result: str, result_image_url: str | None) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(PetitionORM).where(PetitionORM.id == petition_id).values(
                status=PetitionStatus.COMPLETED,
                candidate_result=result,
                candidate_result_image=result_image_url
            )
        )
        await session.flush()

    def _to_domain(self, orm: PetitionORM) -> Petition:
        return Petition(
            id=orm.id, title=orm.title, description=orm.description, region=orm.region,
            scope=orm.scope, image_url=orm.image_url, author_id=orm.author_id,
            author_source=orm.author_source, author_name=orm.author_name,
            support_count=orm.support_count, share_count=orm.share_count,
            view_count=orm.view_count, status=orm.status, candidate_id=orm.candidate_id,
            candidate_name=orm.candidate_name, candidate_progress=orm.candidate_progress,
            candidate_result=orm.candidate_result, candidate_result_image=orm.candidate_result_image,
            created_at=orm.created_at
        )

    async def skip_petition(self, petition_id: int, user_id: int, source: Sources) -> None:
        session = self.__uow.get_session()
        stmt = select(PetitionSkipORM).where(
            PetitionSkipORM.petition_id == petition_id,
            PetitionSkipORM.user_id == user_id,
            PetitionSkipORM.user_source == source
        )
        existing = await session.scalar(stmt)
        if not existing:
            skip_orm = PetitionSkipORM(petition_id=petition_id, user_id=user_id, user_source=source)
            session.add(skip_orm)
            await session.flush()

    async def get_skipped_ids(self, user_id: int, source: Sources) -> list[int]:
        session = self.__uow.get_session()
        stmt = select(PetitionSkipORM.petition_id).where(
            PetitionSkipORM.user_id == user_id,
            PetitionSkipORM.user_source == source
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]