from aiogram.client.session.aiohttp import AiohttpSession
from vkbottle import Bot
from aiogram import Bot as TgBot
from maxapi import Bot as MaxBot

from src.core.di import DeclarativeContainer, providers
from src.domain.entities import Sources
from src.domain.interfaces import (IUnitOfWork, IUserRepository, IStringSorterRepository,
                                   IReferralRepository, IOnlineTaskRepository,
                                   IOfflineTaskRepository, IAcceptedTaskRepository,
                                   ITransactionRepository, ILearningRepository,
                                   IVKTaskVerificationRepository, IS3Storage, IProductRepository,
                                   IOrderRepository, IClosedEventRepository,
                                   IEventRegistrationRepository, IActiveUserRepository,
                                   IParticipationRepository, IHeadlinerRepository,
                                   IVKPublicationRepository)
from src.infrastructure import Database, UnitOfWork
from src.infrastructure.interfaces import IDatabase
from src.infrastructure.repositories import (UserRepository, FuzzywuzzyRepository,
                                             ReferralRepository, TransactionRepository,
                                             AcceptedTaskRepository, OfflineTaskRepository,
                                             OnlineTaskRepository, LearningRepository,
                                             VKTaskVerificationRepository,
                                             EventRegistrationRepository, ClosedEventRepository,
                                             ActiveUserRepository, ParticipationRepository,
                                             HeadlinerRepository, VKPublicationRepository)
from src.infrastructure.repositories.s3_storage import S3Storage
from src.infrastructure.repositories.shop_repo import OrderRepository, ProductRepository
from src.services import UserService, BalanceService, OnlineTaskService, OfflineTaskService
from src.services.active_user_service import ActiveUserService
from src.services.closed_event_service import ClosedEventService
from src.services.interfaces import IUserService, IOfflineTaskService, IOnlineTaskService, \
    IBalanceService, ILearningService, IProductService, IOrderService, IClosedEventService, \
    IActiveUserService, IHeadlinerService
from src.core import config
from src.services.learning_service import LearningService
from src.services.notification_service import NotificationService
from src.services.participation_service import ParticipationService
from src.services.referral_link_service import ReferralLinkService
from src.services.referral_service import ReferralService
from src.services.shop_services import ProductService, OrderService
from src.services.headliner_service import HeadlinerService


class Container(DeclarativeContainer):
    database: providers.Singleton[IDatabase] = providers.Singleton(
        Database, config.DATABASE_URL
    )
    uow: providers.Singleton[IUnitOfWork] = providers.Singleton(
        UnitOfWork, database=database
    )
    bot: providers.Singleton[Bot] = providers.Singleton(Bot, token=config.VK_API_TOKEN)
    tg_bot: providers.Singleton[TgBot] = providers.Singleton(
        TgBot, token=config.TG_API_TOKEN, session=AiohttpSession(proxy=config.proxy)
    )
    max_bot: providers.Singleton[MaxBot] = providers.Singleton(MaxBot, token=config.MAX_API_TOKEN)

    vk_verify_repo: providers.Factory[IVKTaskVerificationRepository] = providers.Factory(
        VKTaskVerificationRepository, service_token=config.SERVICE_TOKEN
    )
    learning_repository: providers.Factory[ILearningRepository] = providers.Factory(
        LearningRepository, uow=uow
    )
    participation_repository: providers.Factory[IParticipationRepository]\
        = providers.Factory(ParticipationRepository, uow=uow)
    user_repository: providers.Factory[IUserRepository] = providers.Factory(
        UserRepository, uow=uow
    )
    string_sorter: providers.Factory[IStringSorterRepository] = providers.Factory(
        FuzzywuzzyRepository
    )
    referral_repository: providers.Factory[IReferralRepository] = providers.Factory(
        ReferralRepository, uow=uow)
    headliner_repository: providers.Factory[IHeadlinerRepository] = providers.Factory(
        HeadlinerRepository, uow=uow)
    vk_publication_repository: providers.Singleton[IVKPublicationRepository] = providers.Singleton(
        VKPublicationRepository,
        token=config.VK_API_TOKEN,
        group_id=config.group_id,
        photo_token=config.VK_PUBLICATION_TOKEN
    )
    online_task_repository: providers.Factory[IOnlineTaskRepository] = providers.Factory(OnlineTaskRepository, uow=uow)
    offline_task_repository: providers.Factory[IOfflineTaskRepository] = providers.Factory(OfflineTaskRepository, uow=uow)
    accepted_task_repository: providers.Factory[IAcceptedTaskRepository] = providers.Factory(AcceptedTaskRepository, uow=uow)
    transaction_repository: providers.Factory[ITransactionRepository] = providers.Factory(TransactionRepository, uow=uow)
    event_repository: providers.Factory[IClosedEventRepository] = providers.Factory(ClosedEventRepository, uow=uow)
    reg_repository: providers.Factory[IEventRegistrationRepository] = providers.Factory(EventRegistrationRepository, uow=uow)
    s3_storage: providers.Singleton[IS3Storage] = providers.Singleton(
        S3Storage, bucket=config.S3_BUCKET, region=config.S3_REGION,
        access_key=config.S3_KEY, secret_key=config.S3_SECRET, endpoint_url=config.S3_ENDPOINT
    )
    product_repository: providers.Factory[IProductRepository] = providers.Factory(ProductRepository,
                                                                                  uow=uow)
    order_repository: providers.Factory[IOrderRepository] = providers.Factory(OrderRepository, uow=uow)
    
    active_user_repository: providers.Factory[IActiveUserRepository] = providers.Factory(
        ActiveUserRepository, uow=uow
    )
    notification_service = providers.Factory(
        NotificationService,
        vk_bot=bot,
        tg_bot=tg_bot,
        max_bot=max_bot
    )
    user_service: providers.Factory[IUserService] = providers.Factory(
        UserService, user_repo=user_repository, uow=uow, string_sorter_repo=string_sorter, 
        source=Sources.VK, transaction_repo=transaction_repository
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
        user_repo=user_repository, balance_svc=balance_service, user_svc=user_service,
        notification_svc=notification_service
    )
    referral_service = providers.Factory(
        ReferralService,
        uow=uow,
        referral_repo=referral_repository,
        user_service=user_service,
        notify_service=notification_service,
        balance_service=balance_service
    )
    referral_link_service = providers.Factory(
        ReferralLinkService,
        vk_bot_link=config.VK_BOT_LINK,
        tg_bot_link=config.TG_BOT_LINK,
        max_bot_link=config.MAX_BOT_LINK,
        source=Sources.VK,
        image_path="docs/image.jpg"
    )
    headliner_service: providers.Factory[IHeadlinerService] = providers.Factory(
        HeadlinerService,
        uow=uow,
        headliner_repo=headliner_repository,
        publication_repo=vk_publication_repository,
        user_service=user_service,
        vk_bot_link=config.VK_BOT_LINK,
        tg_bot_link=config.TG_BOT_LINK,
        max_bot_link=config.MAX_BOT_LINK
    )
    log_chat: providers.Object[str] = providers.Object(config.log_chat)
    admin_ids: providers.Object[list[int]] = providers.Object(config.admin_ids)
    group_id: providers.Object[int] = providers.Object(config.group_id)
    service_token: providers.Object[str] = providers.Object(config.SERVICE_TOKEN)
    verify_chat_id: providers.Object[int] = providers.Object(config.VERIFY_CHAT_ID)

    learning_service: providers.Factory[ILearningService] = providers.Factory(
        LearningService, uow=uow, repo=learning_repository, 
        user_svc=user_service, balance_svc=balance_service
    )
    
    product_service: providers.Factory[IProductService] = providers.Factory(
        ProductService, uow=uow, repo=product_repository,
        s3_storage=s3_storage
    )
    order_service: providers.Factory[IOrderService] = providers.Factory(
        OrderService, uow=uow, repo=order_repository, prod_repo=product_repository,
        balance_svc=balance_service, user_svc=user_service, notif_svc=notification_service
    )
    participation_service = providers.Factory(
        ParticipationService,
        uow=uow,
        participation_repo=participation_repository
    )
    closed_event_service: providers.Factory[IClosedEventService] = providers.Factory(
        ClosedEventService, uow=uow, event_repo=event_repository, reg_repo=reg_repository, user_repo=user_repository
    )
    active_user_service: providers.Factory[IActiveUserService] = providers.Factory(
        ActiveUserService, uow=uow, repo=active_user_repository
    )
