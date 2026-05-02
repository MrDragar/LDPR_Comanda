from aiogram.fsm.state import StatesGroup, State


class RegistrationStates(StatesGroup):
    personal_data = State()
    membership = State()
    surname = State()
    name = State()
    gender = State()
    patronymic = State()
    birth_date = State()
    phone = State()
    email = State()
    region_by_text = State()
    region_by_button = State()
    city = State()
    wish_to_join = State()
    home_address = State()
    news_subscription = State()


class PostsStates(StatesGroup):
    get_message = State()
    confirm = State()


class UploadVideoStates(StatesGroup):
    location = State()
    video = State()
    uploading = State()
