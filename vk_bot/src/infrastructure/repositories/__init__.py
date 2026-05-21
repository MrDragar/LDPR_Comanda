from .user import UserRepository
from .levenshtein import LevenshteinRepository
from .fuzzywuzzy_sorter import FuzzywuzzyRepository
from .referral import ReferralRepository
from .task_repo import OnlineTaskRepository, OfflineTaskRepository, AcceptedTaskRepository
from .balance_repo import TransactionRepository
from .learning import LearningRepository
from .vk_verification import VKTaskVerificationRepository 

__all__ = [
    'UserRepository', 'LevenshteinRepository', 'FuzzywuzzyRepository', 'ReferralRepository',
    'OnlineTaskRepository', 'OfflineTaskRepository', 'AcceptedTaskRepository',
    'TransactionRepository', 'LearningRepository', 'VKTaskVerificationRepository'
]