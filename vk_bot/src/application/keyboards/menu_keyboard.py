import random

from vkbottle import Keyboard, Text

from src.domain.entities.user import UserRole


def get_user_menu_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Выполнить действие", payload=f"{random.randint(0, 1000000)}"))
    kb.add(Text("Мои действия")).row()
    kb.add(Text("Личный кабинет"))
    kb.add(Text("Реферальная ссылка")).row()
    kb.add(Text("Обучение"))
    # kb.add(Text("Магазин")).row()
    kb.add(Text("Закрытые мероприятия")).row()
    return kb.get_json()


def get_role_entry_keyboard(role: UserRole | None) -> str:
    if role is None or role == UserRole.USER:
        return get_user_menu_keyboard()

    kb = Keyboard(one_time=False)
    kb.add(Text("Пользователь"))
    kb.add(Text(role.value)).row()
    return kb.get_json()


def get_staff_ro_menu_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Проверить офлайн задачи"))
    kb.add(Text("Управление заказами")).row()
    kb.add(Text("Список участников мероприятия")).row()
    # kb.add(Text("Назад")).row()
    return kb.get_json()


def get_coordinator_ro_menu_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Проверить офлайн задачи"))
    kb.add(Text("Управление заказами")).row()
    kb.add(Text("Список участников мероприятия")).row()
    kb.add(Text("Создать офлайн задачу"))
    kb.add(Text("Управление пользователями")).row()
    kb.add(Text("Создать закрытое мероприятие")).row()
    # kb.add(Text("Назад")).row()
    return kb.get_json()


def get_staff_ca_menu_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Магазин ЦА"))
    kb.add(Text("Задачи")).row()
    kb.add(Text("Хедлайнеры")).row()
    kb.add(Text("Управление пользователями")).row()
    kb.add(Text("Создать закрытое мероприятие")).row()
    kb.add(Text("Рассылка координаторам РО")).row()
    kb.add(Text("Список участников мероприятия")).row()
    return kb.get_json()


def get_staff_ca_shop_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Добавить товар"))
    kb.add(Text("Скрыть товар")).row()
    kb.add(Text("Управление заказами")).row()
    return kb.get_json()


def get_staff_ca_tasks_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Создать онлайн задачу"))
    kb.add(Text("Создать офлайн задачу")).row()
    kb.add(Text("Проверить офлайн задачи")).row()
    kb.add(Text("Назад к роли")).row()
    return kb.get_json()


def get_staff_ca_headliners_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Добавить хедлайнера"))
    kb.add(Text("Отредактировать хедлайнера")).row()
    kb.add(Text("Удалить хедлайнера"))
    kb.add(Text("Рейтинг хедлайнеров")).row()
    kb.add(Text("Список хедлайнеров"))
    kb.add(Text("Поиск хедлайнера")).row()
    kb.add(Text("Назад к роли")).row()
    return kb.get_json()


def get_headliner_menu_keyboard() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("Личный кабинет"))
    kb.add(Text("Рассылка последователям")).row()
    kb.add(Text("Приветственное сообщение")).row()
    kb.add(Text("Рейтинг хедлайнеров")).row()
    return kb.get_json()


def get_role_tools_keyboard(role: UserRole | None) -> str:
    if role == UserRole.STAFF_CA:
        return get_staff_ca_menu_keyboard()
    if role == UserRole.COORDINATOR_RO:
        return get_coordinator_ro_menu_keyboard()
    if role == UserRole.STAFF_RO:
        return get_staff_ro_menu_keyboard()
    if role == UserRole.HEADLINER:
        return get_headliner_menu_keyboard()
    return get_user_menu_keyboard()


def get_role_menu_keyboard(role: UserRole | None) -> str:
    if role == UserRole.USER:
        return get_user_menu_keyboard()
    if role == UserRole.HEADLINER:
        return get_headliner_menu_keyboard()
    if role == UserRole.STAFF_CA:
        return get_staff_ca_menu_keyboard()
    if role == UserRole.STAFF_RO:
        return get_staff_ro_menu_keyboard()
    if role == UserRole.COORDINATOR_RO:
        return get_coordinator_ro_menu_keyboard()
    return get_role_entry_keyboard(role)
