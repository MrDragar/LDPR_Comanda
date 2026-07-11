import logging
from src.domain.entities.hill import HillVote
from src.domain.entities.user import Sources
from src.domain.exceptions import HillError
from src.domain.interfaces import IHillRepository, IUnitOfWork
from src.services.interfaces import IHillService

logger = logging.getLogger(__name__)


class HillService(IHillService):
    def __init__(self, hill_repo: IHillRepository, uow: IUnitOfWork):
        self.__hill_repo = hill_repo
        self.__uow = uow

    async def get_battle(self, user_id: int, source: Sources) -> dict:
        async with self.__uow.atomic():
            pair = await self.__hill_repo.get_pair_for_user(user_id, source)
            if not pair:
                return {"status": "no_petitions", "message": "Недостаточно петиций для битвы"}

            left, right = pair
            return {
                "left": {
                    "id": left.id,
                    "title": left.title,
                    "description": left.description,
                    "region": left.region,
                    "support_count": left.support_count,
                    "image_url": left.image_url
                },
                "right": {
                    "id": right.id,
                    "title": right.title,
                    "description": right.description,
                    "region": right.region,
                    "support_count": right.support_count,
                    "image_url": right.image_url
                }
            }

    async def make_choice(self, user_id: int, source: Sources, left_id: int, right_id: int,
                          winner_id: int) -> dict:
        async with self.__uow.atomic():
            if winner_id not in [left_id, right_id]:
                raise HillError("Победитель должен быть одним из предложенных")

            vote = HillVote(
                id=0, user_id=user_id, user_source=Sources(source),
                petition_left_id=left_id, petition_right_id=right_id, winner_id=winner_id
            )
            await self.__hill_repo.save_vote(vote)
            return {"status": "success", "message": "Выбор сохранен"}

    async def get_stats(self, user_id: int, source: Sources) -> dict:
        async with self.__uow.atomic():
            count = await self.__hill_repo.get_user_votes_count(user_id, Sources(source))
            return {"total_votes": count}