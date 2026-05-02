import re
from datetime import date

from src.domain.entities.user import User, Sources
from src.domain.exceptions import UserNotFoundError, PhoneBadFormatError, \
    PhoneAlreadyExistsError, PhoneBadCountryError, EmailAlreadyExistsError, \
    EmailBadFormatError, FioFormatError, NotFoundRegionError
from src.domain.interfaces import IUnitOfWork, IUserRepository, \
    IStringSorterRepository
from src.services.interfaces import IUserService


class UserService(IUserService):
    __user_repo: IUserRepository
    __string_sorter_repo: IStringSorterRepository
    __uow: IUnitOfWork
    __region_addresses = {
            'Республика Адыгея (Адыгея)': 'адрес_тестовый', 'Республика Алтай': 'адрес_тестовый', 'Республика Башкортостан': 'адрес_тестовый', 'Республика Бурятия': 'адрес_тестовый', 'Республика Дагестан': 'адрес_тестовый', 'Донецкая Народная Республика': 'адрес_тестовый', 'Республика Ингушетия': 'адрес_тестовый', 'Кабардино-Балкарская Республика': 'адрес_тестовый', 'Республика Калмыкия': 'адрес_тестовый', 'Карачаево-Черкесская Республика': 'адрес_тестовый', 'Республика Карелия': 'адрес_тестовый', 'Республика Коми': 'адрес_тестовый', 'Республика Крым': 'адрес_тестовый', 'Луганская Народная Республика': 'адрес_тестовый', 'Республика Марий Эл': 'адрес_тестовый', 'Республика Мордовия': 'адрес_тестовый', 'Республика Саха (Якутия)': 'адрес_тестовый', 'Республика Северная Осетия - Алания': 'адрес_тестовый', 'Республика Татарстан (Татарстан)': 'адрес_тестовый', 'Республика Тыва': 'адрес_тестовый', 'Удмуртская Республика': 'адрес_тестовый', 'Республика Хакасия': 'адрес_тестовый', 'Чеченская Республика': 'адрес_тестовый', 'Чувашская Республика - Чувашия': 'адрес_тестовый', 'Алтайский край': 'адрес_тестовый', 'Забайкальский край': 'адрес_тестовый', 'Камчатский край': 'адрес_тестовый', 'Краснодарский край': 'адрес_тестовый', 'Красноярский край': 'адрес_тестовый', 'Пермский край': 'адрес_тестовый', 'Приморский край': 'адрес_тестовый', 'Ставропольский край': 'адрес_тестовый', 'Хабаровский край': 'адрес_тестовый', 'Амурская область': 'адрес_тестовый', 'Архангельская область': 'адрес_тестовый', 'Астраханская область': 'адрес_тестовый', 'Белгородская область': 'адрес_тестовый', 'Брянская область': 'адрес_тестовый', 'Владимирская область': 'адрес_тестовый', 'Волгоградская область': 'адрес_тестовый', 'Вологодская область': 'адрес_тестовый', 'Воронежская область': 'адрес_тестовый', 'Запорожская область': 'адрес_тестовый', 'Ивановская область': 'адрес_тестовый', 'Иркутская область': 'адрес_тестовый', 'Калининградская область': 'адрес_тестовый', 'Калужская область': 'адрес_тестовый', 'Кемеровская область - Кузбасс': 'адрес_тестовый', 'Кировская область': 'адрес_тестовый', 'Костромская область': 'адрес_тестовый', 'Курганская область': 'адрес_тестовый', 'Курская область': 'адрес_тестовый', 'Ленинградская область': 'адрес_тестовый', 'Липецкая область': 'адрес_тестовый', 'Магаданская область': 'адрес_тестовый', 'Московская область': 'адрес_тестовый', 'Мурманская область': 'адрес_тестовый', 'Нижегородская область': 'адрес_тестовый', 'Новгородская область': 'адрес_тестовый', 'Новосибирская область': 'адрес_тестовый', 'Омская область': 'адрес_тестовый', 'Оренбургская область': 'адрес_тестовый', 'Орловская область': 'адрес_тестовый', 'Пензенская область': 'адрес_тестовый', 'Псковская область': 'адрес_тестовый', 'Ростовская область': 'адрес_тестовый', 'Рязанская область': 'адрес_тестовый', 'Самарская область': 'адрес_тестовый', 'Саратовская область': 'адрес_тестовый', 'Сахалинская область': 'адрес_тестовый', 'Свердловская область': 'адрес_тестовый', 'Смоленская область': 'адрес_тестовый', 'Тамбовская область': 'адрес_тестовый', 'Тверская область': 'адрес_тестовый', 'Томская область': 'адрес_тестовый', 'Тульская область': 'адрес_тестовый', 'Тюменская область': 'адрес_тестовый', 'Ульяновская область': 'адрес_тестовый', 'Херсонская область': 'адрес_тестовый', 'Челябинская область': 'адрес_тестовый', 'Ярославская область': 'адрес_тестовый', 'Москва': 'адрес_тестовый', 'Санкт-Петербург': 'адрес_тестовый', 'Севастополь - город федерального значения': 'адрес_тестовый', 'Еврейская автономная область': 'адрес_тестовый', 'Ненецкий автономный округ': 'адрес_тестовый', 'Ханты-Мансийский автономный округ - Югра': 'адрес_тестовый', 'Чукотский автономный округ': 'адрес_тестовый', 'Ямало-Ненецкий автономный округ': 'адрес_тестовый'
    }
    __MAX_REGION_SUGGESTIONS = 10
    __source: Sources

    def __init__(self, user_repo: IUserRepository, uow: IUnitOfWork, string_sorter_repo: IStringSorterRepository, source: Sources):
        self.__user_repo = user_repo
        self.__uow = uow
        self.__string_sorter_repo = string_sorter_repo
        self.__source = source

    async def create_user(
            self, user_id: int, username: str | None,
            surname: str, name: str, is_member: bool,
            patronymic: str | None, birth_date: date,
            phone_number: str, region: str, email: str,
            gender: str, city: str, wish_to_join: bool, home_address: str | None,
            news_subscription: bool
    ) -> User:
        user = User(
            id=user_id, source=self.__source, username=username, phone_number=phone_number,
            surname=surname, name=name, patronymic=patronymic,
            birth_date=birth_date, region=region, email=email,
            gender=gender, city=city, wish_to_join=wish_to_join,
            home_address=home_address, is_member=is_member, news_subscription=news_subscription
        )
        async with self.__uow.atomic():
            await self.__user_repo.create_user(user)
        return user
    
    async def get_user_region(self, user_id: int) -> str:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(int(user_id), self.__source)
            except UserNotFoundError:
                raise
            except Exception:
                raise
            return user.region

    async def is_user_exists(self, user_id: int) -> bool:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(int(user_id), self.__source)
            except UserNotFoundError:
                return False
            except Exception:
                raise
            return True

    async def validate_phone(self, phone_number: str) -> str:
        phone_number = phone_number.strip()
        if phone_number.startswith("+7"):
            phone_number = "8" + phone_number[2:]
        digits = []
        for symbol in phone_number:
            if symbol.isdigit():
                digits.append(symbol)
        phone_number = "".join(digits)
        if len(phone_number) != 11:
            raise PhoneBadFormatError
        if not phone_number.startswith("8"):
            raise PhoneBadCountryError

        async with self.__uow.atomic():
            is_existing = await self.__user_repo.is_phone_number_existing(phone_number)
            if is_existing:
                raise PhoneAlreadyExistsError
        return phone_number

    async def validate_email(self, email: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email.strip()):
            raise EmailBadFormatError()

        async with self.__uow.atomic():
            is_existing = await self.__user_repo.is_email_existing(email)
            if is_existing:
                raise EmailAlreadyExistsError
        return email.strip()

    async def validate_fio_part(self, part: str, part_name: str) -> str:
        part_name = part_name.capitalize()
        part = part.strip()

        if not part:
            raise FioFormatError(f"{part_name} не может быть пустым")

        if len(part) < 2:
            raise FioFormatError(
                f"{part_name} не может содержать менее 2 символов")
        if len(part) > 30:
            raise FioFormatError(
                f"{part_name} не может содержать более 30 символов")

        if ' ' in part:
            raise FioFormatError(
                f"{part_name} не может содержать пробелов."
        )

        if not re.match(r'^[А-Яа-яЁё\- ]+$', part):
            raise FioFormatError(
                f"{part_name} может содержать только русские буквы"
            )

        if '  ' in part:
            raise FioFormatError(
                f"{part_name} не может содержать несколько пробелов подряд")

        if '--' in part:
            raise FioFormatError(
                f"{part_name} не может содержать несколько дефисов подряд")
        return part

    async def get_similar_regions(self, region: str) -> list[str]:
        sorted_regions = await self.__string_sorter_repo.sort_by_similarity(
            region, list(self.__region_addresses.keys())
        )
        return sorted_regions[:self.__MAX_REGION_SUGGESTIONS]

    async def get_region_address(self, region: str) -> str:
        if region not in self.__region_addresses:
            raise Exception("Not found a region")
        return self.__region_addresses.get(region)

    async def get_all_users(self) -> list[User]:
        async with self.__uow.atomic():
            return await self.__user_repo.get_users(source=self.__source)

    async def update_news_subscription(
            self, user_id: int, news_subscription: bool
    ) -> User:
        async with self.__uow.atomic():
            return await self.__user_repo.update_user_news_subscription(
                user_id, self.__source, news_subscription
            )

    async def get_region_by_prefix(self, region_prefix: str) -> str:
        for region in self.__region_addresses.keys():
            if region.startswith(region_prefix):
                return region
        raise NotFoundRegionError(f"No such region starting with {region_prefix}")
