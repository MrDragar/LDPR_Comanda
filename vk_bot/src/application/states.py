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


class PostsStates(BaseStateGroup):
    GET_MESSAGE = "get_message"
    CONFIRM = "confirm"
