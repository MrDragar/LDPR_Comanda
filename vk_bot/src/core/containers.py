from src.core.di import DeclarativeContainer, providers
from src.domain.entities import Sources
from src.domain.interfaces import IUnitOfWork, IUserRepository, IStringSorterRepository, \
    IParticipationRepository, IReferralRepository
from src.infrastructure import Database, UnitOfWork
from src.infrastructure.interfaces import IDatabase
from src.infrastructure.repositories import UserRepository, FuzzywuzzyRepository, \
    ParticipationRepository, ReferralRepository
from src.services import UserService
from src.services.interfaces import IUserService
from src.core import config
from src.services.participation_service import ParticipationService
from src.services.referral_link_service import ReferralLinkService
from src.services.referral_service import ReferralService


class Container(DeclarativeContainer):
    database: providers.Singleton[IDatabase] = providers.Singleton(
        Database, "db.sqlite3"
    )
    uow: providers.Singleton[IUnitOfWork] = providers.Singleton(
        UnitOfWork, database=database
    )
    user_repository: providers.Factory[IUserRepository] = providers.Factory(
        UserRepository, uow=uow
    )
    string_sorter: providers.Factory[IStringSorterRepository] = providers.Factory(
        FuzzywuzzyRepository
    )
    participation_repository: providers.Factory[IParticipationRepository]\
        = providers.Factory(ParticipationRepository, uow=uow)
    referral_repository: providers.Factory[IReferralRepository] = providers.Factory(
        ReferralRepository, uow=uow)
    user_service: providers.Factory[IUserService] = providers.Factory(
        UserService, user_repo=user_repository, uow=uow, string_sorter_repo=string_sorter, source=Sources.VK
    )
    participation_service = providers.Factory(
        ParticipationService,
        uow=uow,
        participation_repo=participation_repository
    )
    referral_service = providers.Factory(
        ReferralService,
        uow=uow,
        referral_repo=referral_repository,
        participation_repo=participation_repository,
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
