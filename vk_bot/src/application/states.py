from vkbottle import BaseStateGroup


class RegistrationStates(BaseStateGroup):
    PERSONAL_DATA = "personal_data"
    MERGE_CONFIRM = "merge_confirm"
    AUTH_CODE = "auth_code"
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


class LotteryStates(BaseStateGroup):
    INTRO = "lottery_intro"
    IS_MEMBER = "lottery_is_member"
    EMAIL = "lottery_email"
    GENDER = "lottery_gender"
    CITY = "lottery_city"
    WISH_TO_JOIN = "lottery_wish_to_join"
    HOME_ADDRESS = "lottery_home_address"


class PostsStates(BaseStateGroup):
    GET_MESSAGE = "get_message"
    CONFIRM = "confirm"
    GET_COORD_MESSAGE = "get_coord_message"
    CONFIRM_COORD = "confirm_coord"


class HeadlinerStates(BaseStateGroup):
    CREATE_USER_ID = "headliner_create_user_id"
    CREATE_PHOTO = "headliner_create_photo"
    CREATE_TOPIC = "headliner_create_topic"
    CREATE_FIO = "headliner_create_fio"
    CREATE_POSITION = "headliner_create_position"
    CREATE_GROUP_LINK = "headliner_create_group_link"
    DELETE_ID = "headliner_delete_id"
    EDIT_ID = "headliner_edit_id"
    SEARCH_SURNAME = "headliner_search_surname"
    WELCOME_MESSAGE = "headliner_welcome_message"
    MAILING_MESSAGE = "headliner_mailing_message"
    MAILING_CONFIRM = "headliner_mailing_confirm"


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


class ShopStates(BaseStateGroup):
    BROWSE = "shop_browse"
    DELIVERY_CHOICE = "shop_delivery"
    MAIL_ADDR = "shop_mail_addr"
    MAIL_FIO = "shop_mail_fio"


class AdminShopStates(BaseStateGroup):
    ADD_NAME = "admin_shop_name"
    ADD_DESC = "admin_shop_desc"
    ADD_QTY = "admin_shop_qty"
    ADD_PRICE = "admin_shop_price"
    ADD_PHOTO = "admin_shop_photo"
    HIDE_BROWSE = "admin_hide_browse"


class OrderStates(BaseStateGroup):
    BROWSE = "order_browse"
    CANCEL_REASON = "order_cancel_reason"


class ClosedEventStates(BaseStateGroup):
    BROWSE_USER = "ce_browse_user"
    BROWSE_ADMIN = "ce_browse_admin"
    CREATE = "ce_create"
    PART_LIST = "ce_part_list"


class ProfileStates(BaseStateGroup):
    MAIN = "profile_main"
    REFERRAL = "profile_referral"
    ORDERS = "profile_orders"
    EVENTS = "profile_events"
    RATING = "profile_rating"
