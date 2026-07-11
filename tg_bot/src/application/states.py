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


class UserTaskStates(StatesGroup):
    select_type = State()
    online_list = State()
    online_view = State()
    offline_list = State()
    offline_view = State()
    my_tasks = State()
    tg_online_await_proof = State()
    tg_online_confirm_proof = State()


class AdminTaskStates(StatesGroup):
    create_online = State()
    create_offline = State()
    verify_task_list = State()
    verify_users = State()
    verify_action = State()


class LearningStates(StatesGroup):
    quiz = State()
    
    
class AdminCAStates(StatesGroup):
    search_fio = State()
    search_results = State()


class ClosedEventStates(StatesGroup):
    create = State()
    browse_admin = State()
    part_list = State()
    browse_user = State()
    
    
class PostsStates(StatesGroup):
    get_message = State()
    confirm = State()
    get_coord_message = State()
    confirm_coord = State()


class AdminShopStates(StatesGroup):
    add_name = State()
    add_desc = State()
    add_qty = State()
    add_price = State()
    add_photo = State()
    hide_browse = State()


class OrderStates(StatesGroup):
    browse = State()
    cancel_reason = State()


class ShopStates(StatesGroup):
    browse = State()
    delivery_choice = State()
    mail_addr = State()
    mail_fio = State()


class ProfileStates(StatesGroup):
    menu = State()
    referrals = State()
    orders = State()
    events = State()
    rating = State()


class HeadlinerStates(StatesGroup):
    welcome_message = State()
