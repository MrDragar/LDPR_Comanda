from maxapi.context import StatesGroup, State

class RegistrationStates(StatesGroup):
    PERSONAL_DATA = State()
    MEMBERSHIP = State()
    SURNAME = State()
    NAME = State()
    PATRONYMIC = State()
    GENDER = State()
    BIRTH_DATE = State()
    PHONE = State()
    EMAIL = State()
    REGION_BY_TEXT = State()
    REGION_BY_BUTTON = State()
    CITY = State()
    WISH_TO_JOIN = State()
    HOME_ADDRESS = State()
    NEWS_SUBSCRIPTION = State()
