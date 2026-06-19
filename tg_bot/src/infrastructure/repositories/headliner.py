from sqlalchemy import delete, func, select

from src.domain.entities.headliner import Headliner, HeadlinerFollower
from src.domain.entities.user import Sources
from src.domain.interfaces import IHeadlinerRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.headliner import HeadlinerFollowerORM, HeadlinerORM


class HeadlinerRepository(IHeadlinerRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def create(self, headliner: Headliner) -> Headliner:
        session = self.__uow.get_session()
        headliner_orm = await HeadlinerORM.from_domain(headliner)
        session.add(headliner_orm)
        await session.flush()
        await session.refresh(headliner_orm)
        return await headliner_orm.to_domain()

    async def update(self, headliner_id: int, **kwargs) -> Headliner:
        session = self.__uow.get_session()
        stmt = select(HeadlinerORM).where(HeadlinerORM.id == headliner_id)
        headliner_orm = await session.scalar(stmt)
        if headliner_orm is None:
            raise ValueError(f"Headliner {headliner_id} not found")

        for field, value in kwargs.items():
            if hasattr(headliner_orm, field):
                setattr(headliner_orm, field, value)

        await session.flush()
        await session.refresh(headliner_orm)
        return await headliner_orm.to_domain()

    async def get_by_id(self, headliner_id: int) -> Headliner | None:
        session = self.__uow.get_session()
        stmt = select(HeadlinerORM).where(HeadlinerORM.id == headliner_id)
        headliner = await session.scalar(stmt)
        if headliner is None:
            return None
        return await headliner.to_domain()

    async def get_by_user(self, user_id: int, user_source: Sources) -> Headliner | None:
        session = self.__uow.get_session()
        stmt = select(HeadlinerORM).where(
            HeadlinerORM.user_id == user_id,
            HeadlinerORM.user_source == user_source
        )
        headliner = await session.scalar(stmt)
        if headliner is None:
            return None
        return await headliner.to_domain()

    async def get_all(self) -> list[Headliner]:
        session = self.__uow.get_session()
        result = await session.execute(select(HeadlinerORM).order_by(HeadlinerORM.id))
        return [await headliner.to_domain() for headliner in result.scalars().all()]

    async def delete(self, headliner_id: int) -> Headliner | None:
        session = self.__uow.get_session()
        headliner = await self.get_by_id(headliner_id)
        if headliner is None:
            return None

        await session.execute(delete(HeadlinerORM).where(HeadlinerORM.id == headliner_id))
        await session.flush()
        return headliner

    async def add_follower(
            self,
            headliner_id: int,
            follower_id: int,
            follower_source: Sources
    ) -> HeadlinerFollower:
        session = self.__uow.get_session()
        follower_orm = HeadlinerFollowerORM(
            headliner_id=headliner_id,
            follower_id=follower_id,
            follower_source=follower_source
        )
        session.add(follower_orm)
        await session.flush()
        await session.refresh(follower_orm)
        return await follower_orm.to_domain()

    async def is_follower_exists(self, follower_id: int, follower_source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(HeadlinerFollowerORM).where(
            HeadlinerFollowerORM.follower_id == follower_id,
            HeadlinerFollowerORM.follower_source == follower_source
        ).limit(1)
        return await session.scalar(stmt) is not None

    async def get_followers(self, headliner_id: int) -> list[HeadlinerFollower]:
        session = self.__uow.get_session()
        stmt = select(HeadlinerFollowerORM).where(
            HeadlinerFollowerORM.headliner_id == headliner_id
        )
        result = await session.execute(stmt)
        return [await row.to_domain() for row in result.scalars().all()]

    async def count_followers(self, headliner_id: int) -> int:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(HeadlinerFollowerORM).where(
            HeadlinerFollowerORM.headliner_id == headliner_id
        )
        return await session.scalar(stmt) or 0
