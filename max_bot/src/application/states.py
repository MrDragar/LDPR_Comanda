from maxapi.context import StatesGroup, State


class RegistrationStates(StatesGroup):
    PERSONAL_DATA = State()
    MERGE_CONFIRM = State()
    AUTH_CODE = State()
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


class HeadlinerStates(StatesGroup):
    CREATE_PROFILE_LINK = State()
    CREATE_FIO = State()
    CREATE_PHONE = State()
    CREATE_POSITION = State()
    CREATE_TOPIC = State()
    CREATE_GROUP_LINK = State()
    CREATE_PHOTO = State()
    EDIT_SEARCH = State()
    EDIT_FIELD = State()
    EDIT_VALUE = State()
    DELETE_SEARCH = State()
    SEARCH = State()
    WELCOME_TEXT = State()
    MAILING_TEXT = State()


class UserTaskStates(StatesGroup):
    SELECT_TYPE = State()
    ONLINE_LIST = State()
    ONLINE_VIEW = State()
    OFFLINE_LIST = State()
    OFFLINE_VIEW = State()
    MY_TASKS = State()


class LearningStates(StatesGroup):
    QUIZ = State()


class ShopStates(StatesGroup):
    BROWSE = State()
    DELIVERY_CHOICE = State()
    MAIL_ADDR = State()
    MAIL_FIO = State()


class AdminTaskStates(StatesGroup):
    CREATE_ONLINE = State()
    CREATE_OFFLINE = State()


class AdminShopStates(StatesGroup):
    ADD_NAME = State()
    ADD_DESC = State()
    ADD_QTY = State()
    ADD_PRICE = State()
    HIDE_BROWSE = State()


class AdminCAStates(StatesGroup):
    SEARCH_FIO = State()


class ClosedEventStates(StatesGroup):
    CREATE = State()
