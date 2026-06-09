from maxapi.context import StatesGroup, State


class RegistrationStates(StatesGroup):
    PERSONAL_DATA = State()
    SURNAME = State()
    NAME = State()
    PATRONYMIC = State()
    BIRTH_DATE = State()
    PHONE = State()
    REGION_BY_TEXT = State()
    REGION_BY_BUTTON = State()
    NEWS_SUBSCRIPTION = State()


class LotteryStates(StatesGroup):
    IS_MEMBER = State()
    EMAIL = State()
    GENDER = State()
    CITY = State()
    WISH_TO_JOIN = State()
    HOME_ADDRESS = State()
