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


class UserTaskStates(StatesGroup):
    SELECT_TYPE = State()
    ONLINE_LIST = State()
    ONLINE_VIEW = State()
    OFFLINE_LIST = State()
    OFFLINE_VIEW = State()
    MY_TASKS = State()
    TG_ONLINE_AWAIT_PROOF = State()
    TG_ONLINE_CONFIRM_PROOF = State()


class AdminTaskStates(StatesGroup):
    CREATE_ONLINE = State()
    CREATE_OFFLINE = State()
    VERIFY_TASK_LIST = State()
    VERIFY_USERS = State()
    VERIFY_ACTION = State()


class LearningStates(StatesGroup):
    QUIZ = State()


class AdminCAStates(StatesGroup):
    SEARCH_FIO = State()
    SEARCH_RESULTS = State()


class ClosedEventStates(StatesGroup):
    CREATE = State()
    BROWSE_ADMIN = State()
    PART_LIST = State()
    BROWSE_USER = State()


class AdminShopStates(StatesGroup):
    ADD_NAME = State()
    ADD_DESC = State()
    ADD_QTY = State()
    ADD_PRICE = State()
    ADD_PHOTO = State()
    HIDE_BROWSE = State()


class OrderStates(StatesGroup):
    BROWSE = State()
    CANCEL_REASON = State()


class ShopStates(StatesGroup):
    BROWSE = State()
    DELIVERY_CHOICE = State()
    MAIL_ADDR = State()
    MAIL_FIO = State()


class ProfileStates(StatesGroup):
    MENU = State()
    REFERRALS = State()
    ORDERS = State()
    EVENTS = State()
    RATING = State()


class PostsStates(StatesGroup):
    get_message = State()
    confirm = State()


class HeadlinerStates(StatesGroup):
    welcome_message = State()
