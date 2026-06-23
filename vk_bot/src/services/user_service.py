import re
from datetime import date

from src.domain.entities.user import User, Sources, UserRole, UserGrade
from src.domain.exceptions import UserNotFoundError, PhoneBadFormatError, \
    PhoneAlreadyExistsError, PhoneBadCountryError, EmailAlreadyExistsError, \
    EmailBadFormatError, FioFormatError, NotFoundRegionError, DomainError
from src.domain.interfaces import IUnitOfWork, IUserRepository, \
    IStringSorterRepository, ITransactionRepository
from src.services.interfaces import IUserService


class UserService(IUserService):
    __user_repo: IUserRepository
    __string_sorter_repo: IStringSorterRepository
    __uow: IUnitOfWork
    __region_addresses = {'Республика Адыгея (Адыгея)': 'Республика Адыгея, г. Майкоп, ул. Гоголя 43а', 'Республика Алтай': '649000 Республика Алтай, г. Горно-Алтайск, проспект Коммунистический, д. 36', 'Республика Башкортостан': 'г. Уфа, ул. Советская д.18 (вход со двора)', 'Республика Бурятия': 'Республика Бурятия, г. Улан-Удэ, ул. Ранжурова 1', 'Республика Дагестан': '367000 г. Махачкала, ул. Абубакарова, д.115 (2 этаж)', 'Донецкая Народная Республика': 'Донецкая Народная Республика, Донецк, Буденновский район, Крепильщиков, 181', 'Республика Ингушетия': 'Республика Ингушетия, г. Магас, проспект Идриса Зязикова, д. 50, кв. 2', 'Кабардино-Балкарская Республика': 'г. Нальчик, ул. Ленина, 53 (Здание Федерации профсоюзов КБР), 3 этаж, кабинет 328', 'Республика Калмыкия': '358000 Республика Калмыкия, г. Элиста, ул. Ленина, 249, оф. 202', 'Карачаево-Черкесская Республика': '369000, Карачаево-Черкесская Республика, город Черкесск, Ул. Международная, 62', 'Республика Карелия': '185035, Республика Карелия, г. Петрозаводск, пр. Ленина, д. 16, оф. 17', 'Республика Коми': 'Республика Коми, г. Сыктывкар, ул. Интернациональная д. 131, офис 53', 'Республика Крым': '95000, Республика Крым, г. Симферополь, ул. Турецкая, 14', 'Луганская Народная Республика': '291001, Луганская Народная респ., Луганск г., г.о. город Луганск, ул. Карла Маркса, д. 5, помещ. 55', 'Республика Марий Эл': 'г. Йошкар-Ола, ул. Комсомольская д. 132', 'Республика Мордовия': 'г. Саранск, ул. Б.Хмельницкого, д. 61, пом. 5', 'Республика Саха (Якутия)': '677008 г. Якутск, ул. Петровского, д. 21/2, каб. 202', 'Республика Северная Осетия - Алания': 'РСО-Алания, г. Владикавказ, ул. Виноградная, д. 24', 'Республика Татарстан (Татарстан)': 'г. Казань, ул. Чернышевского, д. 30б', 'Республика Тыва': '667000 Реcпублика Тыва, г. Кызыл, ул. Красноармейская, 76', 'Удмуртская Республика': '426008 г. Ижевск, ул. Карла Маркса, д.208', 'Республика Хакасия': '655017 Республика Хакасия, г. Абакан, ул. Щетинкина, 19 -1н.', 'Чеченская Республика': '364061 Чеченская Республика, г. Грозный, просп. Кадырова, д. 3/25, 24 этаж', 'Чувашская Республика - Чувашия': 'г. Чебоксары, Московский пр.,д.19 к9', 'Алтайский край': '656049 Алтайский край, г. Барнаул, ул. Чкалова, 57', 'Забайкальский край': '672000, г. Чита, ул. Анохина, д. 105, офис 5', 'Камчатский край': 'Камчатский край, г. Петропавловск-Камчатский, ул. Ленинская, д. 34, оф. 10', 'Краснодарский край': '350020, Россия, Краснодарский край, г. Краснодар, ул. Красная, д. 176, офис 902', 'Красноярский край': 'г. Красноярск, пр. Мира, 79 стр.3 (вход со стороны ул. Кирова, в арку)', 'Пермский край': '614068 Пермь, ул. Ленина, д. 102', 'Приморский край': 'Приморский край, г. Владивосток, Проспект 100-летия Владивостока, д.32, кв. 21', 'Ставропольский край': '355017 г. Ставрополь, ул. Пушкина, д. 7', 'Хабаровский край': 'Город Хабаровск, Уссурийский бульвар, 9 (офис 35)', 'Амурская область': '675000 Амурская область, г. Благовещенск, ул. Шимановского, 46/2', 'Архангельская область': '163051 г. Архангельск, ул. Урицкого д. 2', 'Астраханская область': '414040 г. Астрахань, Кировский район, ул. Красная Набережная, 37', 'Белгородская область': '308000, РФ, Белгородская обл., г. Белгород, ул. Н. Островского, д. 19 "в", кв. 48', 'Брянская область': 'г. Брянск, ул. Горького, д. 17', 'Владимирская область': 'г. Владимир, ул. Луначарского, д. 3, каб. 311, 312', 'Волгоградская область': '400066 г. Волгоград, ул. Советская, д. 14А', 'Вологодская область': '160000 г. Вологда, ул. Зосимовская, д. 17, офис 12', 'Воронежская область': '394018 г. Воронеж, ул. Пушкинская, д. 10', 'Запорожская область': '', 'Ивановская область': 'г. Иваново, ул. 10 Августа, 18А (этаж 1)', 'Иркутская область': '664075 г. Иркутск, ул. Дальневосточная, 144, офис 2', 'Калининградская область': '236000 город Калининград, ул. Генделя, 14, кв. 1', 'Калужская область': '248000 г. Калуга, ул. Ленина, 85', 'Кемеровская область - Кузбасс': 'г. Кемерово, ул. Кирова, д. 14', 'Кировская область': 'Кировская область, г. Киров, ул. Ленина, 83', 'Костромская область': 'г. Кострома, ул. Свердлова, д.34.а', 'Курганская область': 'г. Курган, ул. Сибирская, д. 8, оф.12', 'Курская область': 'г. Курск, ул. Красной Армии, д. 23а (2 этаж)', 'Ленинградская область': '191023, Санкт-Петербург, ул. Караванная, д. 1', 'Липецкая область': 'г. Липецк, ул. Зегеля, д. 1 - 65.', 'Магаданская область': 'г. Магадан, проспект Карла Маркса, д. 54', 'Московская область': '107078, г. Москва, 1-й Басманный пер., д. 3, стр. 1', 'Мурманская область': '183038 г. Мурманск, ул. Володарского, д. 13', 'Нижегородская область': 'г. Нижний Новгород, ул. Алексеевская, 3', 'Новгородская область': 'г. Великий Новгород, ул. Большая Санкт-Петергбургская 26', 'Новосибирская область': 'г. Новосибирск, ул. Семьи Шамшиных, д. 77', 'Омская область': 'г. Омск, ул. Гагарина, 2 (ост. Дом Туриста)', 'Оренбургская область': '460000 г. Оренбург, ул. Краснознаменная, 41', 'Орловская область': '302030 Орловская обл., г. Орел, ул. 8 марта, д. 8', 'Пензенская область': '440046 Пензенская область, г. Пенза, ул. Мира, 37', 'Псковская область': 'г. Псков, 180002, ул. Юбилейная, 45', 'Ростовская область': 'г. Ростов-на-Дону, Филимоновская, 128', 'Рязанская область': '390013 Рязанская область, город Рязань, Первомайский проспект, д. 3', 'Самарская область': '443010, Самара, ул. Самарская, д.126, 445044, г. Тольятти, ул. Дзержинского, 38.', 'Саратовская область': 'г. Саратов, ул. Валовая, д. 15', 'Сахалинская область': 'г. Южно-Сахалинск, пр. Мира, д. 190, офис 1', 'Свердловская область': 'Свердловская область, город Екатеринбург, ул. 8 Марта, 13, офис: 57-67 (правый подъезд)', 'Смоленская область': '214000 г. Смоленск, ул. Дзержинского, д. 2', 'Тамбовская область': 'Тамбов, пл. Привокзальная, д. 14А, кв. 17', 'Тверская область': '170100 Тверская область, г. Тверь, Лидии Базановой, д.20, оф. 31', 'Томская область': '634012 г.Томск, ул.Елизаровых, д. 39, оф.1', 'Тульская область': 'г. Тула, ул. Советская, д.7, офис 38', 'Тюменская область': 'г. Тюмень, ул. Советская, д. 61, офис 104', 'Ульяновская область': '432017 г. Ульяновск, ул. Железной Дивизии, д. 6', 'Херсонская область': 'Россия, Херсонская область, Геническ, ул. Нижняя Слободка, д.1б', 'Челябинская область': 'г. Челябинск, пр. Ленина, д. 12-17', 'Ярославская область': '150000 Ярославская область, город Ярославль, улица Кирова, д. 4 (1 этаж)', 'Москва': '107078, г. Москва, 1-й басманный переулок д 3 стр 1', 'Санкт-Петербург': '197198, г. Санкт-Петербург, ул. Маркина, д. 12А', 'Севастополь - город федерального значения': '299011 г. Севастополь, ул. Большая Морская, д. 32', 'Еврейская автономная область': '679000, Еврейская Автономная Область г. Биробиджан, ул. Пионерская, д. 3;', 'Ненецкий автономный округ': '166000, г. Нарьян-Мар, ул. Южная, д. 18 А, кв.2', 'Ханты-Мансийский автономный округ - Югра': '628402 Ханты-Мансийский автономный округ - Югра, город Сургут, улица Набережная Ивана Кайдалова, дом 28, подъезд 5.', 'Чукотский автономный округ': '689000 Чукотский автономный округ, г. Анадырь, ул. Отке, д. 29, каб. 4', 'Ямало-Ненецкий автономный округ': 'г. Салехард, ул. Губкина, д. 13, каб. 6'}
    __MAX_REGION_SUGGESTIONS = 10
    __source: Sources

    def __init__(
            self, user_repo: IUserRepository, uow: IUnitOfWork, 
            string_sorter_repo: IStringSorterRepository, transaction_repo: ITransactionRepository,
            source: Sources):
        self.__user_repo = user_repo
        self.__uow = uow
        self.__string_sorter_repo = string_sorter_repo
        self.__transaction_repo = transaction_repo
        self.__source = source

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
    ) -> User:
        user = User(
            id=user_id, source=self.__source, username=username, phone_number=phone_number,
            surname=surname, name=name, patronymic=patronymic,
            birth_date=birth_date, region=region, email=email,
            gender=gender, city=city, wish_to_join=wish_to_join,
            home_address=home_address, is_member=is_member, news_subscription=news_subscription
        )
        async with self.__uow.atomic():
            return await self.__user_repo.create_user(user)

    async def update_user_profile(
        self, user_id: int, source: Sources,
        birth_date: date | None = None,
        email: str | None = None,
        gender: str | None = None,
        city: str | None = None,
        wish_to_join: bool | None = None,
        is_member: bool | None = None, 
        home_address: str | None = None
    ) -> User:
        updates = {}
        if email is not None:
            updates['email'] = email
        if gender is not None:
            updates['gender'] = gender
        if city is not None:
            updates['city'] = city
        if wish_to_join is not None:
            updates['wish_to_join'] = wish_to_join
        if is_member is not None:
            updates['is_member'] = is_member
        if home_address is not None:
            updates['home_address'] = home_address
        if birth_date is not None:
            updates['birth_date'] = birth_date
        async with self.__uow.atomic():
            return await self.__user_repo.update_user_profile(user_id, source, **updates)

    async def get_user_region(self, user_id: int) -> str:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(int(user_id), self.__source)
            except UserNotFoundError:
                raise
            except Exception:
                raise
            return user.region

    async def is_user_exists(self, user_id: int, inviter_source: Sources | None = None) -> bool:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(
                    int(user_id),
                    inviter_source or self.__source
                )
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
            is_existing = await self.__user_repo.is_phone_number_existing(phone_number, self.__source)
            if is_existing:
                raise PhoneAlreadyExistsError
        return phone_number

    async def validate_email(self, email: str | None) -> str | None:
        if email is None:
            return email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email.strip()):
            raise EmailBadFormatError()

        async with self.__uow.atomic():
            is_existing = await self.__user_repo.is_email_existing(email, self.__source)
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
    
    async def get_user_role(self, user_id: int, user_source: Sources) -> UserRole:
        async with self.__uow.atomic():
            try:
                user = await self.__user_repo.get_user(int(user_id), user_source)
                return user.role
            except UserNotFoundError:
                raise DomainError("Пользователь не найден")
            except Exception:
                raise DomainError("Ошибка при получении роли")
            
    async def get_user(self, user_id: int, user_source: Sources) -> User:
        async with self.__uow.atomic():
            return await self.__user_repo.get_user(user_id, user_source)

    async def search_users_by_fio(self, surname: str, name: str, patronymic: str | None, skip: int, limit: int) -> list[User]:
        async with self.__uow.atomic():
            return await self.__user_repo.search_by_fio(surname, name, patronymic, skip, limit)

    async def update_user_role(self, user_id: int, source: Sources, role: UserRole) -> None:
        async with self.__uow.atomic():
            await self.__user_repo.update_user_role(user_id, source, role)

    async def get_completed_tasks_count(self, user_id: int, source: Sources, is_online: bool) -> int:
        async with self.__uow.atomic():
            return await self.__user_repo.get_completed_tasks_count(user_id, source, is_online)

    async def update_user_grade(self, user_id: int, source: Sources, grade: UserGrade) -> None:
        async with self.__uow.atomic():
            await self.__user_repo.update_user_grade(user_id, source, grade)
    
    async def get_user_rating(self, user_id: int, source: Sources) -> int:
        async with self.__uow.atomic():
            return await self.__transaction_repo.get_user_rating(user_id, source)

    async def get_global_top(self, limit: int = 10) -> list[dict]:
        async with self.__uow.atomic():
            top = await self.__transaction_repo.get_global_top(limit)
            res = []
            for uid, score, source in top:
                try:
                    u = await self.__user_repo.get_user(uid, source)
                    res.append({"name": f"{u.surname} {u.name}", "score": score, "uid": uid})
                except: pass
            return res

    async def get_local_top(self, region: str, limit: int = 10) -> list[dict]:
        async with self.__uow.atomic():
            top = await self.__transaction_repo.get_local_top(region, limit)
            res = []
            for uid, score, source in top:
                try:
                    u = await self.__user_repo.get_user(uid, source)
                    res.append({"name": f"{u.surname} {u.name}", "score": score, "uid": uid})
                except: pass
            return res

    async def get_users_by_role(self, role: UserRole) -> list[User]:
        async with self.__uow.atomic():
            return await self.__user_repo.get_users(role=role, source=self.__source)
