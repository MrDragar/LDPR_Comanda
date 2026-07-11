import logging
from datetime import datetime

from src.domain.entities.user import User, Sources
from src.domain.exceptions import AuthError, AuthBadUserError, UserNotFoundError, \
    UserAlreadyExistsError
from src.domain.interfaces import IUserRepository, IJWTRepository, ITelegramAuthRepository, IVKAuthRepository, IMaxAuthRepository, IUnitOfWork
from src.services.interfaces import IAuthService

logger = logging.getLogger(__name__)

class AuthService(IAuthService):
    def __init__(self, user_repo: IUserRepository, jwt_repo: IJWTRepository,
                 tg_auth_repo: ITelegramAuthRepository, vk_auth_repo: IVKAuthRepository,
                 max_auth_repo: IMaxAuthRepository, uow: IUnitOfWork):
        self.__user_repo = user_repo
        self.__jwt_repo = jwt_repo
        self.__tg_auth_repo = tg_auth_repo
        self.__vk_auth_repo = vk_auth_repo
        self.__max_auth_repo = max_auth_repo
        self.__uow = uow

    async def authenticate_tg(self, auth_data: str) -> str:
        user_id = await self.__tg_auth_repo.verify_data(auth_data)
        return await self.__generate_token(user_id, Sources.TG)

    async def authenticate_vk(self, auth_data: str) -> str:
        user_id = await self.__vk_auth_repo.verify_data(auth_data)
        return await self.__generate_token(user_id, Sources.VK)

    async def authenticate_max(self, auth_data: str) -> str:
        user_id = await self.__max_auth_repo.verify_data(auth_data)
        return await self.__generate_token(user_id, Sources.MAX)

    async def __generate_token(self, user_id: int, source: Sources) -> str:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(user_id, source)
            except UserNotFoundError:
                raise AuthBadUserError("Пользователь не найден. Пройдите регистрацию в боте.")
            except Exception as e:
                logger.error(f"Auth error: {e}")
                raise AuthError("Ошибка авторизации")
        return await self.__jwt_repo.create_access_token(user_id, source)

    async def get_user_by_token(self, token: str) -> User:
        try:
            user_id, source_str = await self.__jwt_repo.decode_access_token(token)
            source = source_str
            async with self.__uow.atomic():
                user = await self.__user_repo.get_user(user_id, source)
            return user
        except AuthError:
            raise
        except UserNotFoundError:
            raise AuthBadUserError("Пользователь не найден")
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            raise AuthError("Некорректный токен")

    async def register(self, auth_data: str, source: str, user_data: dict) -> str:
        # 1. Верификация auth_data в зависимости от источника
        if source == "tg":
            user_id = await self.__tg_auth_repo.verify_data(auth_data)
            src_enum = Sources.TG
        elif source == "vk":
            user_id = await self.__vk_auth_repo.verify_data(auth_data)
            src_enum = Sources.VK
        elif source == "max":
            user_id = await self.__max_auth_repo.verify_data(auth_data)
            src_enum = Sources.MAX
        else:
            raise AuthError("Некорректный источник")

        # 2. Проверка существования и создание
        async with self.__uow.atomic():
            try:
                await self.__user_repo.get_user(user_id, src_enum)
                raise UserAlreadyExistsError("Пользователь уже зарегистрирован")
            except UserNotFoundError:
                pass  # Пользователя нет, продолжаем регистрацию

            # Парсинг даты рождения, если пришла строкой
            birth_date = user_data.get("birth_date")
            if isinstance(birth_date, str):
                try:
                    birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
                except ValueError:
                    birth_date = None

            # 3. Создание пользователя (используем user_repo напрямую, чтобы не трогать user_service)
            user = User(
                id=user_id,
                source=src_enum,
                username=user_data.get("username"),
                surname=user_data.get("surname"),
                name=user_data.get("name"),
                patronymic=user_data.get("patronymic"),
                phone_number=user_data.get("phone_number"),
                birth_date=birth_date,
                region=user_data.get("region"),
                email=user_data.get("email"),
                gender=user_data.get("gender"),
                city=user_data.get("city"),
                wish_to_join=user_data.get("wish_to_join"),
                home_address=user_data.get("home_address"),
                news_subscription=user_data.get("news_subscription", False),
                is_member=user_data.get("is_member")
            )
            await self.__user_repo.create_user(user)

        # 4. Генерация JWT
        return await self.__jwt_repo.create_access_token(user_id, src_enum)

    async def update_user_profile(self, user_id: int, source: Sources, **kwargs) -> User:
        async with self.__uow.atomic():
            return await self.__user_repo.update_user_profile(user_id, source, **kwargs)
