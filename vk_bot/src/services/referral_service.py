import logging
from src.domain.entities.user import Sources
from src.domain.interfaces import IUnitOfWork, IReferralRepository
from src.services.interfaces import IReferralService, IUserService, IBalanceService, INotificationService

logger = logging.getLogger(__name__)


class ReferralService(IReferralService):
    def __init__(
            self, uow: IUnitOfWork, referral_repo: IReferralRepository, user_service: IUserService,
            balance_service: IBalanceService, notify_service: INotificationService
    ):
        self.__uow = uow
        self.__referral_repo = referral_repo
        self.__user_service = user_service
        self.__balance_service = balance_service
        self.__notify_service = notify_service

    async def activate_referral(self, inviter_id: int, inviter_source: Sources, invitee_id: int,
                                invitee_source: Sources) -> None:
        if not await self.__user_service.is_user_exists(inviter_id, inviter_source):
            return
        if inviter_id == invitee_id and inviter_source == invitee_source:
            return
        async with self.__uow.atomic():
            is_already_referral = await self.__referral_repo.is_invitee_exists(invitee_id,
                                                                               invitee_source)
            if is_already_referral:
                logger.debug(
                    f"User {invitee_id} (source: {invitee_source.value}) is already a referral.")
                return

            old_count = await self.__referral_repo.get_count_invitees(inviter_id, inviter_source)
            await self.__balance_service.add_balance(
                inviter_id, inviter_source, 10,f"Награда за реферала"
            )
            await self.__notify_service.notify_user(
                inviter_id, inviter_source, "Вам начислено 10 баллов за привлечение реферала"
            )
            await self.__referral_repo.add(inviter_id, inviter_source, invitee_id, invitee_source)

    async def get_count_invitees(self, inviter: int, inviter_source: Sources) -> int:
        async with self.__uow.atomic():
            return await self.__referral_repo.get_count_invitees(inviter, inviter_source)
