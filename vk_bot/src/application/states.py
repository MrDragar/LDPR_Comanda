from vkbottle import BaseStateGroup


class RegistrationStates(BaseStateGroup):
    PERSONAL_DATA = "personal_data"
    MEMBERSHIP = "membership"
    SURNAME = "surname"
    NAME = "name"
    GENDER = "gender"
    PATRONYMIC = "patronymic"
    BIRTH_DATE = "birth_date"
    PHONE = "phone"
    EMAIL = "email"
    REGION_BY_TEXT = "region_by_text"
    REGION_BY_BUTTON = "region_by_button"
    CITY = "city"
    WISH_TO_JOIN = "wish_to_join"
    HOME_ADDRESS = "home_address"
    NEWS_SUBSCRIPTION = "news_subscription"
    CHECK_SUBSCRIPTION = "check_subscription"


class PostsStates(BaseStateGroup):
    GET_MESSAGE = "get_message"
    CONFIRM = "confirm"


class AdminCAStates(BaseStateGroup):
    SEARCH_FIO = "ca_search_fio"
    SEARCH_RESULTS = "ca_search_results"
    SELECT_USER = "ca_select_user"
    CHANGE_ROLE = "ca_change_role"


class AdminTaskStates(BaseStateGroup):
    CREATE_ONLINE = "admin_create_online"
    CREATE_OFFLINE = "admin_create_offline"
    VERIFY_TASK_LIST = "admin_verify_list"
    VERIFY_USERS = "admin_verify_users"
    VERIFY_ACTION = "admin_verify_action"


class UserTaskStates(BaseStateGroup):
    SELECT_TYPE = "user_select_type"
    ONLINE_LIST = "user_online_list"
    ONLINE_VIEW = "user_online_view"
    OFFLINE_LIST = "user_offline_list"
    OFFLINE_VIEW = "user_offline_view"
    MY_TASKS = "user_my_tasks"
    MY_TASK_VIEW = "user_my_task_view"


class LearningStates(BaseStateGroup):
    QUIZ = "learning_quiz"
