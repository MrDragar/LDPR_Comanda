from abc import ABC, abstractmethod
from contextlib import _AsyncGeneratorContextManager
from datetime import date

from .entities import User, Sources, LearningTestAttempt
from .entities.task import OnlineTask, OfflineTask, AcceptedOnlineTask, AcceptedOfflineTask, \
    Transaction, TaskStatus, TaskType


class IUnitOfWork(ABC):
    @abstractmethod
    def atomic(self) -> _AsyncGeneratorContextManager[None, None]:
        ...


class IUserRepository(ABC):
    @abstractmethod
    async def create_user(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_user(self, user_id: int, source: Sources) -> User:
        ...

    @abstractmethod
    async def is_phone_number_existing(self, phone_number: str) -> bool:
        ...
    
    @abstractmethod
    async def is_email_existing(self, email: str) -> bool:
        ...

    @abstractmethod
    async def update_user_balance(self, user_id: int, source: Sources, new_balance: int) -> None:
        ...

    @abstractmethod
    async def update_user_role(self, user_id: int, source: Sources, role) -> None:
        ...
    
    @abstractmethod
    async def search_by_fio(self, surname: str, name: str, patronymic: str | None, skip: int, limit: int) -> list[User]: ...

    @abstractmethod
    async def get_completed_tasks_count(self, user_id: int, source: Sources, is_online: bool) -> int: ...

    @abstractmethod
    async def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> list[User]:
        ...

    @abstractmethod
    async def update_user_news_subscription(
            self, user_id: int, source: Sources, news_subscription: bool
    ) -> User:
        ...

    @abstractmethod
    async def update_user_grade(self, user_id: int, source: Sources, grade) -> None:
        ...


class IStringSorterRepository(ABC):
    @abstractmethod
    async def sort_by_similarity(self, target: str, string_list: list[str]) -> list[str]:
        ...


class IReferralRepository(ABC):
    @abstractmethod
    async def add(self, inviter_id: int, inviter_source: Sources, invitee_id: int, invitee_source: Sources) -> None:
        ...

    @abstractmethod
    async def is_invitee_exists(self, invitee_id: int, invitee_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_count_invitees(self, inviter_id: int, inviter_source: Sources) -> int:
        ...


class IOnlineTaskRepository(ABC):
    @abstractmethod
    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date, skip: int, limit: int) -> tuple[list[OnlineTask], int]: ...
    @abstractmethod
    async def get_task_by_id(self, task_id: int) -> OnlineTask | None: ...
    @abstractmethod
    async def create_task(self, task: OnlineTask) -> OnlineTask: ...
    @abstractmethod
    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources, task_id: int) -> bool: ...


class IOfflineTaskRepository(ABC):
    @abstractmethod
    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date, skip: int, limit: int) -> tuple[list[OfflineTask], int]: ...
    @abstractmethod
    async def get_task_by_id(self, task_id: int) -> OfflineTask | None: ...
    @abstractmethod
    async def create_task(self, task: OfflineTask) -> OfflineTask: ...
    @abstractmethod
    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources, task_id: int) -> bool: ...


class IAcceptedTaskRepository(ABC):
    @abstractmethod
    async def accept_online_task(self, accepted: AcceptedOnlineTask) -> AcceptedOnlineTask:
        ...

    @abstractmethod
    async def update_offline_task_status(self, user_id: int, user_source: Sources, task_id: int, status: TaskStatus) -> None:
        ...

    @abstractmethod
    async def get_user_accepted_offline_tasks(self, user_id: int, user_source: Sources, skip: int, limit: int) -> tuple[list[AcceptedOfflineTask], int]:
        ...

    @abstractmethod
    async def cancel_accepted_task(self, user_id: int, user_source: Sources, task_id: int, is_online: bool) -> None:
        ...

    @abstractmethod
    async def get_in_progress_for_task(self, task_id: int, skip: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]: ...

    @abstractmethod
    async def create_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        ...

    @abstractmethod
    async def get_in_progress_users_for_task(self, task_id: int, skip: int, limit: int) -> tuple[list[AcceptedOfflineTask], int]:
        ...

    @abstractmethod
    async def add_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        ...


class ITransactionRepository(ABC):
    @abstractmethod
    async def add_transaction(self, transaction: Transaction) -> Transaction:
        ...


class ILearningRepository(ABC):
    @abstractmethod
    async def get_attempt(self, user_id: int, user_source: Sources) -> LearningTestAttempt | None: ...
    @abstractmethod
    async def save_attempt(self, attempt: LearningTestAttempt) -> None: ...


class IVKTaskVerificationRepository(ABC):
    @abstractmethod
    async def verify_task(self, task_type: TaskType, user_id: int, group_id: int, post_id: int) -> bool:
        """Проверяет выполнение действия пользователя над постом сообщества"""
        ...
