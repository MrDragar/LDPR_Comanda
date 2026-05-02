import logging
from src.domain.entities.user import Sources
from src.domain.interfaces import IUnitOfWork, IReferralRepository
from src.services.interfaces import IReferralService

logger = logging.getLogger(__name__)


class ReferralService(IReferralService):
    def __init__(self, uow: IUnitOfWork, referral_repo: IReferralRepository):
        self.__uow = uow
        self.__referral_repo = referral_repo

    async def activate_referral(self, inviter_id: int, inviter_source: Sources, invitee_id: int,
                                invitee_source: Sources) -> None:
        async with self.__uow.atomic():
            is_already_referral = await self.__referral_repo.is_invitee_exists(invitee_id,
                                                                               invitee_source)
            if is_already_referral:
                logger.debug(
                    f"User {invitee_id} (source: {invitee_source.value}) is already a referral.")
                return

            await self.__referral_repo.add(inviter_id, inviter_source, invitee_id, invitee_source)

    async def get_count_invitees(self, inviter: int, inviter_source: Sources) -> int:
        async with self.__uow.atomic():
            return await self.__referral_repo.get_count_invitees(inviter, inviter_source)
