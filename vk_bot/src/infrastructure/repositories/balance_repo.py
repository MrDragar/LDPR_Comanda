import logging
from sqlalchemy import select, func, text
from src.domain.entities.task import Transaction
from src.domain.entities.user import Sources
from src.domain.interfaces import ITransactionRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.task import TransactionORM
from src.infrastructure.models.user import UserORM

logger = logging.getLogger(__name__)


class TransactionRepository(ITransactionRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def add_transaction(self, transaction: Transaction) -> Transaction:
        session = self.__uow.get_session()
        orm = TransactionORM(
            user_id=transaction.user_id, user_source=transaction.user_source,
            amount=transaction.amount, description=transaction.description
        )
        session.add(orm)

        stmt = select(UserORM).where(UserORM.id == transaction.user_id,
                                     UserORM.source == transaction.user_source)
        user_orm = await session.scalar(stmt)
        if user_orm:
            user_orm.balance += transaction.amount
            logger.info(
                f"Transaction {transaction.amount} added for user {transaction.user_id}. New balance: {user_orm.balance}")
        else:
            logger.error(f"User {transaction.user_id} not found for balance update")

        await session.flush()
        transaction.id = orm.id
        return transaction

    async def get_user_rating(self, user_id: int, user_source: Sources) -> int:
        session = self.__uow.get_session()
        stmt = select(func.coalesce(func.sum(TransactionORM.amount), 0)).where(
            TransactionORM.user_id == user_id,
            TransactionORM.user_source == user_source,
            TransactionORM.amount > 0
        )
        return int(await session.scalar(stmt) or 0)

    async def get_global_top(self, limit: int = 10) -> list[tuple[int, int, Sources]]:
        session = self.__uow.get_session()
        stmt = select(
            TransactionORM.user_id, TransactionORM.user_source,
            func.coalesce(func.sum(TransactionORM.amount), 0).label("total")
        ).where(
            TransactionORM.amount > 0
        ).group_by(TransactionORM.user_id, TransactionORM.user_source).order_by(text("total DESC")).limit(
            limit)
        result = await session.execute(stmt)
        return [(row.user_id, int(row.total), row.user_source) for row in result.all()]

    async def get_local_top(self, region: str, limit: int = 10) -> list[tuple[int, int, Sources]]:
        session = self.__uow.get_session()
        stmt = select(
            TransactionORM.user_id, TransactionORM.user_source,
            func.coalesce(func.sum(TransactionORM.amount), 0).label("total")
        ).join(
            UserORM,
            (UserORM.id == TransactionORM.user_id) & (UserORM.source == TransactionORM.user_source)
        ).where(
            TransactionORM.amount > 0,
            UserORM.region == region
        ).group_by(TransactionORM.user_id, TransactionORM.user_source).order_by(text("total DESC")).limit(
            limit)
        result = await session.execute(stmt)
        return [(row.user_id, int(row.total), row.user_source) for row in result.all()]
