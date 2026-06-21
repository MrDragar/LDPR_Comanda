from abc import ABC, abstractmethod
from datetime import date, time
from src.domain.entities import Repost, Sources, User, OrderStatus, Order, Product, \
    EventRegistration, ClosedEvent
from src.domain.entities.headliner import Headliner, HeadlinerFollower
from src.domain.entities.task import OnlineTask, OfflineTask, AcceptedOfflineTask, TaskStatus, \
    TaskType
from src.domain.entities.user import UserRole


class IUserService(ABC):
    @abstractmethod
    async def create_user(
            self, user_id: int, username: str | None, surname: str, name: str | None,
            patronymic: str | None, phone_number: str, region: str | None,
            news_subscription: bool,
            birth_date: date | None = None,
            email: str | None = None,
            gender: str | None = None,
            city: str | None = None,
            wish_to_join: bool | None = None,
            is_member: bool | None = None,
            home_address: str | None = None
    ) -> User: ...

    @abstractmethod
    async def update_user_profile(
            self, user_id: int, source: Sources,
            birth_date: date | None = None,
            email: str | None = None,
            gender: str | None = None,
            city: str | None = None,
            wish_to_join: bool | None = None,
            is_member: bool | None = None,
            home_address: str | None = None
    ) -> User: ...

    @abstractmethod
    async def is_user_exists(self, user_id: int, inviter_source: Sources | None = None) -> bool: ...
    @abstractmethod
    async def validate_phone(self, phone_number: str) -> str: ...
    @abstractmethod
    async def validate_email(self, email: str | None) -> str | None: ...
    @abstractmethod
    async def validate_fio_part(self, part: str, part_name: str) -> str: ...
    @abstractmethod
    async def get_similar_regions(self, region: str) -> list[str]: ...
    @abstractmethod
    async def get_region_address(self, region: str) -> str: ...
    @abstractmethod
    async def get_user_region(self, user_id: int) -> str: ...
    @abstractmethod
    async def get_all_users(self) -> list[User]: ...
    @abstractmethod
    async def update_news_subscription(self, user_id: int, news_subscription: bool) -> User: ...
    @abstractmethod
    async def get_region_by_prefix(self, region_prefix: str) -> str: ...
    @abstractmethod
    async def get_user_role(self, user_id: int, user_source: Sources) -> UserRole: ...
    @abstractmethod
    async def get_user(self, user_id: int, user_source: Sources) -> User: ...
    @abstractmethod
    async def search_users_by_fio(self, surname: str, name: str, patronymic: str | None, skip: int, limit: int) -> list[User]: ...
    @abstractmethod
    async def update_user_role(self, user_id: int, source: Sources, role: UserRole) -> None: ...
    @abstractmethod
    async def get_completed_tasks_count(self, user_id: int, source: Sources, is_online: bool) -> int: ...
    @abstractmethod
    async def update_user_grade(self, user_id: int, source: Sources, grade) -> None: ...
    @abstractmethod
    async def get_user_rating(self, user_id: int, source: Sources) -> int: ...
    @abstractmethod
    async def get_global_top(self, limit: int = 10) -> list[dict]: ...
    @abstractmethod
    async def get_local_top(self, region: str, limit: int = 10) -> list[dict]: ...
    @abstractmethod
    async def get_users_by_role(self, role: UserRole) -> list[User]: ...


class IBalanceService(ABC):
    @abstractmethod
    async def get_balance(self, user_id: int, user_source: Sources) -> int: ...
    @abstractmethod
    async def add_balance(self, user_id: int, user_source: Sources, amount: int, description: str) -> None: ...
    @abstractmethod
    async def deduct_balance(self, user_id: int, user_source: Sources, amount: int, description: str) -> None: ...


class IOnlineTaskService(ABC):
    @abstractmethod
    async def search_tasks(self, user_id: int, user_source: Sources, page: int = 1, is_member: bool | None = None) -> tuple[list[OnlineTask], int]: ...
    @abstractmethod
    async def check_task(self, user_id: int, user_source: Sources, task_id: int) -> None: ...
    @abstractmethod
    async def get_task(self, task_id: int) -> OnlineTask | None: ...
    @abstractmethod
    async def create_task(self, date: date, duration: int, type: TaskType, reward: int, url: str | None, title: str, description: str, is_for_members: bool) -> OnlineTask: ...
    @abstractmethod
    async def submit_tg_online_task(self, user_id: int, user_source: Sources, task_id: int) -> None: ...
    @abstractmethod
    async def accept_tg_online_task(self, user_id: int, user_source: Sources, task_id: int) -> None: ...
    @abstractmethod
    async def decline_tg_online_task(self, user_id: int, user_source: Sources, task_id: int) -> None: ...


class IOfflineTaskService(ABC):
    @abstractmethod
    async def search_tasks(self, user_id: int, user_source: Sources, page: int = 1, is_member: bool | None = None) -> tuple[list[OfflineTask], int]: ...
    @abstractmethod
    async def check_task(self, user_id: int, user_source: Sources, task_id: int, new_status: TaskStatus) -> None: ...
    @abstractmethod
    async def get_task(self, task_id: int) -> OfflineTask | None: ...
    @abstractmethod
    async def get_user_tasks(self, user_id: int, user_source: Sources, page: int = 1) -> tuple[list[AcceptedOfflineTask], int]: ...
    @abstractmethod
    async def cancel_task(self, user_id: int, user_source: Sources, task_id: int) -> None: ...

    @abstractmethod
    async def create_task_by_admin(self, region: str, start_date: date, duration: int, reward: int, title: str, description: str, location: str, contacts: str, is_for_members: bool) -> OfflineTask: ...

    @abstractmethod
    async def create_task_by_personal(self, user_id: int, user_source: Sources, start_date: date, duration: int, reward: int, title: str, description: str, location: str, contacts: str, is_for_members: bool) -> OfflineTask: ...

    @abstractmethod
    async def get_in_progress_users(self, task_id: int, page: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]: ...
    
    @abstractmethod
    async def get_users_for_task(self, task_id: int, page: int = 1, limit: int = 10) -> tuple[
        list[AcceptedOfflineTask], int]: ...

    @abstractmethod
    async def accept_offline_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        ...


class IReferralService(ABC):
    @abstractmethod
    async def activate_referral(self, inviter_id: int, inviter_source: Sources, invitee_id: int,
                                invitee_source: Sources) -> None:
        ...

    @abstractmethod
    async def get_count_invitees(self, inviter: int, inviter_source: Sources) -> int:
        ...


class IReferralLinkService(ABC):
    vk_bot_link: str
    tg_bot_link: str
    max_bot_link: str
    source: Sources

    @abstractmethod
    def generate_post(self, user_id: int) -> Repost:
        ...


class IHeadlinerService(ABC):
    @abstractmethod
    async def create_headliner(
            self,
            user_id: int,
            fio: str,
            position: str,
            topic: str,
            group_link: str,
            photo: str | None
    ) -> Headliner:
        ...

    @abstractmethod
    async def publish_article(self, headliner: Headliner) -> tuple[int | None, str | None]:
        ...

    @abstractmethod
    async def get_by_user(self, user_id: int, user_source: Sources) -> Headliner | None:
        ...

    @abstractmethod
    async def get_by_id(self, headliner_id: int) -> Headliner | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[Headliner]:
        ...

    @abstractmethod
    async def delete_headliner(self, headliner_id: int) -> Headliner | None:
        ...

    @abstractmethod
    async def get_rating(self) -> list[tuple[Headliner, int]]:
        ...

    @abstractmethod
    async def update_welcome_message_by_user(
            self,
            user_id: int,
            user_source: Sources,
            welcome_message: str
    ) -> Headliner | None:
        ...

    @abstractmethod
    async def attach_follower(
            self,
            headliner_id: int,
            follower_id: int,
            follower_source: Sources
    ) -> HeadlinerFollower | None:
        ...

    @abstractmethod
    async def get_followers(self, headliner_id: int) -> list[HeadlinerFollower]:
        ...

    @abstractmethod
    async def count_followers(self, headliner_id: int) -> int:
        ...

    @abstractmethod
    def make_referral_links(self, headliner_id: int) -> dict[str, str]:
        ...
    

class INotificationService(ABC):
    @abstractmethod
    async def notify_user(self, user_id: int, source: Sources, text: str) -> None: ...



class ILearningService(ABC):
    @abstractmethod
    async def get_question(self, question_index: int) -> tuple[str, list[str], int]: ...
    @abstractmethod
    async def finish_quiz(self, user_id: int, user_source: Sources, score: int) -> dict: ...
    @abstractmethod
    async def is_learning_passed(self, user_id: int, user_source: Sources) -> bool: ...
    
    
class IProductService(ABC):
    @abstractmethod
    async def list_products(self, page: int) -> tuple[list[Product], int]: ...
    @abstractmethod
    async def create_product(self, name: str, desc: str, price: int, qty: int, photo_bytes: bytes) -> Product: ...
    @abstractmethod
    async def hide_product(self, product_id: int) -> None: ...
    @abstractmethod
    async def get_product(self, product_id: int) -> Product | None: ...


class IOrderService(ABC):
    @abstractmethod
    async def create_order(self, user_id: int, source: Sources, product_id: int, delivery_type: str, address: str | None, fio: str | None) -> Order: ...
    @abstractmethod
    async def get_user_orders(self, user_id: int, source: Sources, page: int) -> tuple[list[Order], int]: ...
    @abstractmethod
    async def get_admin_orders(self, admin_region: str | None, page: int) -> tuple[list[Order], int]: ...
    @abstractmethod
    async def update_order_status(self, order_id: int, new_status: OrderStatus, reason: str | None = None) -> Order: ...
    @abstractmethod
    async def get_user_orders_history(self, user_id: int, source: Sources) -> list[Order]: ...


class IClosedEventService(ABC):
    @abstractmethod
    async def create_event(self, title: str, desc: str, loc: str, d: date, t: time, region: str) -> ClosedEvent: ...
    @abstractmethod
    async def list_events(self, region: str | None, page: int) -> tuple[list[ClosedEvent], int]: ...
    @abstractmethod
    async def register(self, user_id: int, source: Sources, event_id: int) -> None: ...
    @abstractmethod
    async def list_participants(self, event_id: int, page: int) -> tuple[list[EventRegistration], int]: ...
    @abstractmethod
    async def get_event(self, event_id: int) -> ClosedEvent | None: ...
    @abstractmethod
    async def get_user_events(self, user_id: int, source: Sources) -> list[ClosedEvent]: ...


class IActiveUserService(ABC):
    @abstractmethod
    async def log_active_user(self, user_id: int, user_source: Sources) -> None: ...


class IParticipationService(ABC):
    @abstractmethod
    async def is_participant(self, user_id: int, user_source: Sources) -> bool:
        ...

    @abstractmethod
    async def activate_participation(self, user_id: int, user_source: Sources) -> int:
        ...

    @abstractmethod
    async def get_all_participation_ids(self, user_id: int, user_source: Sources) -> list[int]:
        ...
