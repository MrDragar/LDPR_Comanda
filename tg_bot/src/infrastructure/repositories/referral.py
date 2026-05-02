from sqlalchemy import select, func
from src.domain.entities.user import Sources
from src.domain.interfaces import IReferralRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.referral import ReferralORM


class ReferralRepository(IReferralRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def add(self, inviter_id: int, inviter_source: Sources, invitee_id: int, invitee_source: Sources) -> None:
        session = self.__uow.get_session()
        referral_orm = ReferralORM(
            inviter_id=inviter_id,
            inviter_source=inviter_source,
            invitee_id=invitee_id,
            invitee_source=invitee_source
        )
        session.add(referral_orm)

    async def is_invitee_exists(self, invitee_id: int, invitee_source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(ReferralORM).where(
            ReferralORM.invitee_id == invitee_id,
            ReferralORM.invitee_source == invitee_source
        ).limit(1)
        result = await session.scalar(stmt)
        return result is not None

    async def get_count_invitees(self, inviter_id: int, inviter_source: Sources) -> int:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(ReferralORM).where(
            ReferralORM.inviter_id == inviter_id,
            ReferralORM.inviter_source == inviter_source
        )
        return await session.scalar(stmt) or 0
