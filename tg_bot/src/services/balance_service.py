import logging
from src.domain.entities.user import Sources
from src.domain.entities.task import Transaction
from src.domain.interfaces import IUnitOfWork, IUserRepository, ITransactionRepository
from src.services.interfaces import IBalanceService
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


class BalanceService(IBalanceService):
    def __init__(self, uow: IUnitOfWork, user_repo: IUserRepository, transaction_repo: ITransactionRepository):
        self.__uow = uow
        self.__user_repo = user_repo
        self.__transaction_repo = transaction_repo

    async def get_balance(self, user_id: int, user_source: Sources) -> int:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(user_id, user_source)
                return user.balance
            except Exception:
                raise DomainError("Ошибка получения баланса")

    async def add_balance(self, user_id: int, user_source: Sources, amount: int, description: str) -> None:
        if amount <= 0:
            raise DomainError("Сумма пополнения должна быть больше нуля")
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(user_id, user_source)
                transaction = Transaction(id=0, user_id=user_id, user_source=user_source, amount=amount, description=description)
                await self.__transaction_repo.add_transaction(transaction)
                logger.info(f"Balance updated for user {user_id}. Added {amount}")
            except DomainError:
                raise
            except Exception as e:
                logger.error(f"Error adding balance: {e}")
                raise DomainError("Ошибка при начислении баллов")

    async def deduct_balance(self, user_id: int, user_source: Sources, amount: int,
                             description: str) -> None:
        if amount <= 0:
            raise DomainError("Сумма списания должна быть больше нуля")

        async with self.__uow.atomic():
            user = await self.__user_repo.get_user(user_id, user_source)
            if user.balance < amount:
                raise DomainError(
                    f"Недостаточно баллов для списания. Текущий баланс: {user.balance}, требуется: {amount}"
                )

            # Создаём транзакцию с отрицательным значением
            transaction = Transaction(
                id=0, user_id=user_id, user_source=user_source,
                amount=-amount, description=description
            )
            await self.__transaction_repo.add_transaction(transaction)
            logger.info(f"Balance updated for user {user_id}. Deducted {amount} ({description})")
