from aiogram.client.session.aiohttp import AiohttpSession
from vkbottle import Bot
from aiogram import Bot as TgBot

from src.core.di import DeclarativeContainer, providers
from src.domain.entities import Sources
from src.domain.interfaces import (IUnitOfWork, IUserRepository, IStringSorterRepository,
                                   IReferralRepository, IOnlineTaskRepository,
                                   IOfflineTaskRepository, IAcceptedTaskRepository,
                                   ITransactionRepository, ILearningRepository,
                                   IVKTaskVerificationRepository, IS3Storage, IProductRepository,
                                   IOrderRepository)
from src.infrastructure import Database, UnitOfWork
from src.infrastructure.interfaces import IDatabase
from src.infrastructure.repositories import (UserRepository, FuzzywuzzyRepository,
                                             ReferralRepository, TransactionRepository,
                                             AcceptedTaskRepository, OfflineTaskRepository,
                                             OnlineTaskRepository, LearningRepository,
                                             VKTaskVerificationRepository)
from src.infrastructure.repositories.s3_storage import S3Storage
from src.infrastructure.repositories.shop_repo import OrderRepository, ProductRepository
from src.services import UserService, BalanceService, OnlineTaskService, OfflineTaskService
from src.services.interfaces import IUserService, IOfflineTaskService, IOnlineTaskService, \
    IBalanceService, ILearningService, IProductService, IOrderService
from src.core import config
from src.services.learning_service import LearningService
from src.services.notification_service import NotificationService
from src.services.referral_link_service import ReferralLinkService
from src.services.referral_service import ReferralService
from src.services.shop_services import ProductService, OrderService


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
    vk_verify_repo: providers.Factory[IVKTaskVerificationRepository] = providers.Factory(
        VKTaskVerificationRepository, service_token=config.SERVICE_TOKEN
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
    s3_storage: providers.Singleton[IS3Storage] = providers.Singleton(
        S3Storage, bucket=config.S3_BUCKET, region=config.S3_REGION,
        access_key=config.S3_KEY, secret_key=config.S3_SECRET, endpoint_url=config.S3_ENDPOINT
    )
    product_repo: providers.Factory[IProductRepository] = providers.Factory(ProductRepository,
                                                                            uow=uow)
    order_repo: providers.Factory[IOrderRepository] = providers.Factory(OrderRepository, uow=uow)
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
        user_svc=user_service, notification_svc=notification_service,
        vk_verify_repo=vk_verify_repo
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
    
    product_service: providers.Factory[IProductService] = providers.Factory(
        ProductService, uow=uow, repo=product_repo,
        s3_storage=s3_storage
    )
    order_service: providers.Factory[IOrderService] = providers.Factory(
        OrderService, uow=uow, repo=order_repo, prod_repo=product_repo,
        balance_svc=balance_service, user_svc=user_service, notif_svc=notification_service
    )
