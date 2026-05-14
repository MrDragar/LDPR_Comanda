import logging
from sqlalchemy import select
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
