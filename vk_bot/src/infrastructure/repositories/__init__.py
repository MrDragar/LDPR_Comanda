from .user import UserRepository
from .levenshtein import LevenshteinRepository
from .fuzzywuzzy_sorter import FuzzywuzzyRepository
from .referral import ReferralRepository
from .headliner import HeadlinerRepository
from .vk_publication import VKPublicationRepository
from .task_repo import OnlineTaskRepository, OfflineTaskRepository, AcceptedTaskRepository
from .balance_repo import TransactionRepository
from .learning import LearningRepository
from .vk_verification import VKTaskVerificationRepository
from .closed_event_repo import ClosedEventRepository, EventRegistrationRepository
from .active_user import ActiveUserRepository
from .participation import ParticipationRepository
from .auth import JWTRepository, TelegramAuthRepository, VKAuthRepository, MaxAuthRepository
from .petition import PetitionRepository
from .candidate import CandidateRepository, CandidateQuestionRepository
from .stats import StatsRepository
from .hill import HillRepository


__all__ = [
    'UserRepository', 'LevenshteinRepository', 'FuzzywuzzyRepository', 'ReferralRepository',
    'HeadlinerRepository', 'VKPublicationRepository',
    'OnlineTaskRepository', 'OfflineTaskRepository', 'AcceptedTaskRepository',
    'TransactionRepository', 'LearningRepository', 'VKTaskVerificationRepository',
    'ClosedEventRepository', 'EventRegistrationRepository', 'ActiveUserRepository',
    'ParticipationRepository', 'JWTRepository', 'TelegramAuthRepository', 'VKAuthRepository',
    'MaxAuthRepository', 'PetitionRepository', 'CandidateRepository', 'CandidateQuestionRepository',
    'StatsRepository', 'HillRepository'
]
