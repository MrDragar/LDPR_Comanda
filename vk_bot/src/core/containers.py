from aiogram.client.session.aiohttp import AiohttpSession
from vkbottle import Bot
from aiogram import Bot as TgBot

from src.core.di import DeclarativeContainer, providers
from src.domain.entities import Sources
from src.domain.interfaces import (IUnitOfWork, IUserRepository, IStringSorterRepository,
                                   IReferralRepository, IOnlineTaskRepository,
                                   IOfflineTaskRepository, IAcceptedTaskRepository,
                                   ITransactionRepository, ILearningRepository)
from src.infrastructure import Database, UnitOfWork
from src.infrastructure.interfaces import IDatabase
from src.infrastructure.repositories import (UserRepository, FuzzywuzzyRepository,
                                             ReferralRepository, TransactionRepository,
                                             AcceptedTaskRepository, OfflineTaskRepository,
                                             OnlineTaskRepository, LearningRepository)
from src.services import UserService, BalanceService, OnlineTaskService, OfflineTaskService
from src.services.interfaces import IUserService, IOfflineTaskService, IOnlineTaskService, \
    IBalanceService, ILearningService
from src.core import config
from src.services.learning_service import LearningService
from src.services.notification_service import NotificationService
from src.services.referral_link_service import ReferralLinkService
from src.services.referral_service import ReferralService


class Container(DeclarativeContainer):
    database: providers.Singleton[IDatabase] = providers.Singleton(
        Database, "db.sqlite3"
    )
    uow: providers.Singleton[IUnitOfWork] = providers.Singleton(
        UnitOfWork, database=database
    )
    bot: providers.Singleton[Bot] = providers.Singleton(Bot, token=config.VK_API_TOKEN)
    tg_bot: providers.Singleton[TgBot] = providers.Singleton(
        TgBot, token=config.TG_API_TOKEN, session=AiohttpSession(proxy=config.proxy)
    )
    learning_repository: providers.Factory[ILearningRepository] = providers.Factory(
        LearningRepository, uow=uow
    )
    user_repository: providers.Factory[IUserRepository] = providers.Factory(
        UserRepository, uow=uow
    )
    string_sorter: providers.Factory[IStringSorterRepository] = providers.Factory(
        FuzzywuzzyRepository
    )
    referral_repository: providers.Factory[IReferralRepository] = providers.Factory(
        ReferralRepository, uow=uow)
    online_task_repository: providers.Factory[IOnlineTaskRepository] = providers.Factory(OnlineTaskRepository, uow=uow)
    offline_task_repository: providers.Factory[IOfflineTaskRepository] = providers.Factory(OfflineTaskRepository, uow=uow)
    accepted_task_repository: providers.Factory[IAcceptedTaskRepository] = providers.Factory(AcceptedTaskRepository, uow=uow)
    transaction_repository: providers.Factory[ITransactionRepository] = providers.Factory(TransactionRepository, uow=uow)
    notification_service = providers.Factory(
        NotificationService,
        vk_bot=bot,
        tg_bot=tg_bot
    )
    user_service: providers.Factory[IUserService] = providers.Factory(
        UserService, user_repo=user_repository, uow=uow, string_sorter_repo=string_sorter, source=Sources.VK
    )
    balance_service: providers.Factory[IBalanceService] = providers.Factory(
        BalanceService, uow=uow, user_repo=user_repository, transaction_repo=transaction_repository
    )
    online_task_service: providers.Factory[IOnlineTaskService] = providers.Factory(
        OnlineTaskService, uow=uow, task_repo=online_task_repository,
        accepted_repo=accepted_task_repository, balance_svc=balance_service,
        user_svc=user_service, notification_svc=notification_service
    )
    offline_task_service: providers.Factory[IOfflineTaskService] = providers.Factory(
        OfflineTaskService, uow=uow, task_repo=offline_task_repository, accepted_repo=accepted_task_repository, 
        user_repo=user_repository, balance_svc=balance_service, user_svc=user_service
    )
    referral_service = providers.Factory(
        ReferralService,
        uow=uow,
        referral_repo=referral_repository,
        user_service=user_service
    )
    referral_link_service = providers.Factory(
        ReferralLinkService,
        vk_bot_link=config.VK_BOT_LINK,
        tg_bot_link=config.TG_BOT_LINK,
        source=Sources.VK,
        image_path="docs/gifts.png"
    )
    log_chat: providers.Object[str] = providers.Object(config.log_chat)
    admin_ids: providers.Object[list[int]] = providers.Object(config.admin_ids)
    group_id: providers.Object[int] = providers.Object(config.group_id)

    learning_service: providers.Factory[ILearningService] = providers.Factory(
        LearningService, uow=uow, repo=learning_repository, 
        user_svc=user_service, balance_svc=balance_service
    )
