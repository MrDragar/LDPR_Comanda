from abc import ABC, abstractmethod
from contextlib import _AsyncGeneratorContextManager
from datetime import date

from .entities import User, Sources, LearningTestAttempt, Product, Order, OrderStatus, ClosedEvent, \
    EventRegistration, Petition, PetitionStatus, CandidateQuestion, Candidate, HillVote
from .entities.headliner import Headliner, HeadlinerFollower
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
    async def update_user_profile(self, user_id: int, source: Sources, **kwargs) -> User:
        ...

    @abstractmethod
    async def get_user(self, user_id: int, source: Sources) -> User:
        ...

    @abstractmethod
    async def is_phone_number_existing(self, phone_number: str, source: Sources) -> bool:
        ...

    @abstractmethod
    async def is_email_existing(self, email: str, source: Sources) -> bool:
        ...

    @abstractmethod
    async def update_user_balance(self, user_id: int, source: Sources, new_balance: int) -> None:
        ...

    @abstractmethod
    async def update_user_role(self, user_id: int, source: Sources, role) -> None:
        ...

    @abstractmethod
    async def search_by_fio(self, surname: str, name: str, patronymic: str | None, skip: int,
                            limit: int) -> list[User]: ...

    @abstractmethod
    async def get_completed_tasks_count(self, user_id: int, source: Sources,
                                        is_online: bool) -> int: ...

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
    async def add(self, inviter_id: int, inviter_source: Sources, invitee_id: int,
                  invitee_source: Sources) -> None:
        ...

    @abstractmethod
    async def is_invitee_exists(self, invitee_id: int, invitee_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_count_invitees(self, inviter_id: int, inviter_source: Sources) -> int:
        ...


class IHeadlinerRepository(ABC):
    @abstractmethod
    async def create(self, headliner: Headliner) -> Headliner:
        ...

    @abstractmethod
    async def update(self, headliner_id: int, **kwargs) -> Headliner:
        ...

    @abstractmethod
    async def get_by_id(self, headliner_id: int) -> Headliner | None:
        ...

    @abstractmethod
    async def get_by_user(self, user_id: int, user_source: Sources) -> Headliner | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[Headliner]:
        ...

    @abstractmethod
    async def delete(self, headliner_id: int) -> Headliner | None:
        ...

    @abstractmethod
    async def add_follower(
            self,
            headliner_id: int,
            follower_id: int,
            follower_source: Sources
    ) -> HeadlinerFollower:
        ...

    @abstractmethod
    async def is_follower_exists(self, follower_id: int, follower_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_followers(self, headliner_id: int) -> list[HeadlinerFollower]:
        ...

    @abstractmethod
    async def count_followers(self, headliner_id: int) -> int:
        ...


class IVKPublicationRepository(ABC):
    @abstractmethod
    async def publish_headliner(
            self,
            name: str,
            description: str,
            photo: str | None
    ) -> int | None:
        ...


class IOnlineTaskRepository(ABC):
    @abstractmethod
    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int, is_member: bool | None = None) -> \
    tuple[list[OnlineTask], int]: ...

    @abstractmethod
    async def get_task_by_id(self, task_id: int) -> OnlineTask | None: ...

    @abstractmethod
    async def create_task(self, task: OnlineTask) -> OnlineTask: ...

    @abstractmethod
    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources,
                                       task_id: int) -> bool: ...

    @staticmethod
    @abstractmethod
    def _parse_vk_url(url: str) -> tuple[int, int]: ...


class IOfflineTaskRepository(ABC):
    @abstractmethod
    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int, is_member: bool | None = None) -> \
    tuple[list[OfflineTask], int]: ...

    @abstractmethod
    async def get_task_by_id(self, task_id: int) -> OfflineTask | None: ...

    @abstractmethod
    async def create_task(self, task: OfflineTask) -> OfflineTask: ...

    @abstractmethod
    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources,
                                       task_id: int) -> bool: ...


class IAcceptedTaskRepository(ABC):
    @abstractmethod
    async def accept_online_task(self, accepted: AcceptedOnlineTask) -> AcceptedOnlineTask:
        ...

    @abstractmethod
    async def update_offline_task_status(self, user_id: int, user_source: Sources, task_id: int,
                                         status: TaskStatus) -> None:
        ...

    @abstractmethod
    async def get_user_accepted_offline_tasks(self, user_id: int, user_source: Sources, skip: int,
                                              limit: int) -> tuple[list[AcceptedOfflineTask], int]:
        ...

    @abstractmethod
    async def cancel_accepted_task(self, user_id: int, user_source: Sources, task_id: int,
                                   is_online: bool) -> None:
        ...

    @abstractmethod
    async def get_in_progress_for_task(self, task_id: int, skip: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]: ...

    @abstractmethod
    async def create_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        ...

    @abstractmethod
    async def get_in_progress_users_for_task(self, task_id: int, skip: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]:
        ...

    @abstractmethod
    async def add_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        ...

    @abstractmethod
    async def update_online_task_status(self, user_id: int, user_source: Sources, task_id: int,
                                        status: TaskStatus) -> None:
        ...


class ITransactionRepository(ABC):
    @abstractmethod
    async def add_transaction(self, transaction: Transaction) -> Transaction: ...

    @abstractmethod
    async def get_user_rating(self, user_id: int, user_source: Sources) -> int: ...

    @abstractmethod
    async def get_global_top(self, limit: int = 10) -> list[tuple[int, int, Sources]]: ...

    @abstractmethod
    async def get_local_top(self, region: str, limit: int = 10) -> list[tuple[int, int, Sources]]:
        ...


class ILearningRepository(ABC):
    @abstractmethod
    async def get_attempt(self, user_id: int,
                          user_source: Sources) -> LearningTestAttempt | None: ...

    @abstractmethod
    async def save_attempt(self, attempt: LearningTestAttempt) -> None: ...

    @abstractmethod
    async def is_passed(self, user_id: int, user_source: Sources) -> bool: ...


class IVKTaskVerificationRepository(ABC):
    @abstractmethod
    async def verify_task(self, task_type: TaskType, user_id: int, group_id: int,
                          post_id: int) -> bool:
        """Проверяет выполнение действия пользователя над постом сообщества"""
        ...


class IProductRepository(ABC):
    @abstractmethod
    async def get_active_products(self, skip: int, limit: int) -> tuple[list[Product], int]: ...

    @abstractmethod
    async def get_by_id(self, product_id: int) -> Product | None: ...

    @abstractmethod
    async def create(self, product: Product) -> Product: ...

    @abstractmethod
    async def update_quantity(self, product_id: int, new_quantity: int) -> None: ...

    @abstractmethod
    async def toggle_active(self, product_id: int, is_active: bool) -> None: ...


class IOrderRepository(ABC):
    @abstractmethod
    async def create(self, order: Order) -> Order: ...

    @abstractmethod
    async def get_pending_by_user(self, user_id: int, user_source: Sources, skip: int,
                                  limit: int) -> tuple[list[Order], int]: ...

    @abstractmethod
    async def get_pending_by_admin(self, admin_region: str | None, skip: int, limit: int) -> tuple[
        list[Order], int]: ...

    @abstractmethod
    async def update_status(self, order_id: int, status: OrderStatus,
                            reason: str | None = None) -> Order: ...

    @abstractmethod
    async def get_by_id(self, order_id: int) -> Order | None: ...

    @abstractmethod
    async def has_user_ordered_product(self, user_id: int, user_source: Sources,
                                       product_id: int) -> bool: ...

    @abstractmethod
    async def get_all_by_user(self, user_id: int, user_source: Sources) -> list[Order]: ...


class IS3Storage(ABC):
    @abstractmethod
    async def upload_photo(self, file_bytes: bytes, filename: str) -> str: ...
    @abstractmethod
    async def generate_presigned_put_url(self, object_key: str, content_type: str, expires_in: int = 3600) -> str: ...


class IClosedEventRepository(ABC):
    @abstractmethod
    async def create(self, event: ClosedEvent) -> ClosedEvent: ...

    @abstractmethod
    async def get_by_id(self, event_id: int) -> ClosedEvent | None: ...

    @abstractmethod
    async def get_active_by_region(self, region: str | None, skip: int, limit: int) -> tuple[
        list[ClosedEvent], int]: ...

    @abstractmethod
    async def get_user_events(self, user_id: int, user_source: Sources) -> list[ClosedEvent]: ...


class IEventRegistrationRepository(ABC):
    @abstractmethod
    async def register_user(self, user_id: int, user_source: Sources,
                            event_id: int) -> EventRegistration: ...

    @abstractmethod
    async def is_registered(self, user_id: int, user_source: Sources, event_id: int) -> bool: ...

    @abstractmethod
    async def get_participants(self, event_id: int, skip: int, limit: int) -> tuple[
        list[EventRegistration], int]: ...


class IActiveUserRepository(ABC):
    @abstractmethod
    async def save_if_not_exists(self, user_id: int, user_source: Sources) -> None: ...


class IParticipationRepository(ABC):
    @abstractmethod
    async def add(self, user_id: int, user_source: Sources) -> int:
        ...

    @abstractmethod
    async def is_participant(self, user_id: int, user_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_all_participation_ids(self, user_id: int, user_source: Sources) -> list[int]:
        ...


class IJWTRepository(ABC):
    @abstractmethod
    async def create_access_token(self, user_id: int, source: Sources,
                                  expires_delta: int | None = None) -> str: ...

    @abstractmethod
    async def decode_access_token(self, token: str) -> tuple[int, Sources]: ...


class IVKAuthRepository(ABC):
    @abstractmethod
    async def verify_data(self, auth_data: str) -> int: ...


class ITelegramAuthRepository(ABC):
    @abstractmethod
    async def verify_data(self, auth_data: str) -> int: ...


class IMaxAuthRepository(ABC):
    @abstractmethod
    async def verify_data(self, auth_data: str) -> int: ...


class IPetitionRepository(ABC):
    @abstractmethod
    async def create(self, petition: Petition) -> Petition: ...

    @abstractmethod
    async def get_by_id(self, petition_id: int) -> Petition | None: ...

    @abstractmethod
    async def get_feed(self, scope: str | None, region: str | None, limit: int, user_id: int | None = None, source: Sources | None = None) -> list[Petition]: ...

    @abstractmethod
    async def get_all(self, scope: str | None, status: str | None, region: str | None, page: int,
                      limit: int) -> tuple[list[Petition], int]: ...

    @abstractmethod
    async def get_my(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[list[Petition], int]: ...

    @abstractmethod
    async def get_supported(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[list[Petition], int]: ...

    @abstractmethod
    async def support(self, petition_id: int, user_id: int, source: Sources) -> bool: ...

    @abstractmethod
    async def is_supported(self, petition_id: int, user_id: int, source: Sources) -> bool: ...

    @abstractmethod
    async def increment_share(self, petition_id: int) -> None: ...

    @abstractmethod
    async def increment_view(self, petition_id: int) -> None: ...

    @abstractmethod
    async def update_status(self, petition_id: int, status: PetitionStatus) -> None: ...

    @abstractmethod
    async def get_available_for_candidate(self, region: str, page: int, limit: int) -> tuple[list[Petition], int]: ...
    @abstractmethod
    async def get_by_candidate(self, candidate_id: int, status: str, page: int, limit: int) -> tuple[list[Petition], int]: ...
    @abstractmethod
    async def take_petition(self, petition_id: int, candidate_id: int, candidate_name: str, initial_comment: str) -> None: ...
    @abstractmethod
    async def update_progress(self, petition_id: int, comment: str) -> None: ...
    @abstractmethod
    async def complete_petition(self, petition_id: int, result: str, result_image_url: str | None) -> None: ...
    @abstractmethod
    async def skip_petition(self, petition_id: int, user_id: int, source: Sources) -> None: ...
    @abstractmethod
    async def get_skipped_ids(self, user_id: int, source: Sources) -> list[int]: ...

class ICandidateRepository(ABC):
    @abstractmethod
    async def create(self, candidate: Candidate) -> Candidate: ...
    @abstractmethod
    async def get_all(self, region: str | None, page: int, limit: int) -> tuple[list[Candidate], int]: ...
    @abstractmethod
    async def get_by_id(self, candidate_id: int) -> Candidate | None: ...
    @abstractmethod
    async def get_by_user_id(self, user_id: int, source: Sources) -> Candidate | None: ...
    @abstractmethod
    async def get_petitions_counts(self, candidate_id: int) -> tuple[int, int]: ...
    @abstractmethod
    async def get_petitions_by_status(self, candidate_id: int, status: str) -> list[dict]: ...


class ICandidateQuestionRepository(ABC):
    @abstractmethod
    async def create(self, question: CandidateQuestion) -> CandidateQuestion: ...
    @abstractmethod
    async def get_by_id(self, question_id: int) -> CandidateQuestion | None: ...
    @abstractmethod
    async def get_for_candidate(self, candidate_id: int, status: str | None, page: int, limit: int) -> tuple[list[CandidateQuestion], int]: ...
    @abstractmethod
    async def update_answer(self, question_id: int, text: str | None, voice_url: str | None, video_url: str | None) -> None: ...
    @abstractmethod
    async def get_by_author(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[list[CandidateQuestion], int]: ...


class IStatsRepository(ABC):
    @abstractmethod
    async def get_region_user_count(self, region: str) -> int: ...
    @abstractmethod
    async def get_user_weekly_stats(self, user_id: int, source: Sources) -> dict: ...


class IHillRepository(ABC):
    @abstractmethod
    async def get_pair_for_user(self, user_id: int, source: Sources) -> tuple[
                                                                            Petition, Petition] | None: ...

    @abstractmethod
    async def save_vote(self, vote: HillVote) -> HillVote: ...

    @abstractmethod
    async def get_user_votes_count(self, user_id: int, source: Sources) -> int: ...
