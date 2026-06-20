from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.domain.entities.user import UserRole


def _keyboard(rows: list[list[str]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[MessageButton(text=text) for text in row])
    return builder


def get_user_menu_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Выполнить задание", "Мои задания"],
        ["Личный кабинет", "Обучение"],
        ["Магазин"],
        ["Закрытые мероприятия"],
    ])


def get_role_entry_keyboard(role: UserRole | None) -> InlineKeyboardBuilder:
    if role is None or role == UserRole.USER:
        return get_user_menu_keyboard()
    return _keyboard([["Пользователь", role.value]])


def get_staff_ro_menu_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Проверить офлайн задачи"],
        ["Управление заказами"],
        ["Список участников мероприятия"],
    ])


def get_coordinator_ro_menu_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Проверить офлайн задачи"],
        ["Управление заказами"],
        ["Список участников мероприятия"],
        ["Создать офлайн задачу"],
        ["Управление пользователями"],
        ["Создать закрытое мероприятие"],
    ])


def get_staff_ca_menu_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Магазин ЦА", "Задачи"],
        ["Хедлайнеры"],
        ["Управление пользователями"],
        ["Создать закрытое мероприятие"],
        ["Рассылка координаторам РО"],
        ["Список участников мероприятия"],
    ])


def get_staff_ca_shop_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Добавить товар", "Скрыть товар"],
        ["Управление заказами"],
    ])


def get_staff_ca_tasks_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Создать онлайн задачу"],
        ["Создать офлайн задачу"],
        ["Проверить офлайн задачи"],
        ["Назад"],
    ])


def get_staff_ca_headliners_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Добавить хедлайнера"],
        ["Отредактировать хедлайнера"],
        ["Удалить хедлайнера"],
        ["Рейтинг хедлайнеров"],
        ["Список хедлайнеров"],
        ["Поиск хедлайнера"],
        ["Назад"],
    ])


def get_headliner_menu_keyboard() -> InlineKeyboardBuilder:
    return _keyboard([
        ["Личный кабинет"],
        ["Рассылка последователям"],
        ["Приветственное сообщение"],
        ["Рейтинг хедлайнеров"],
    ])


def get_role_tools_keyboard(role: UserRole | None) -> InlineKeyboardBuilder:
    if role == UserRole.STAFF_CA:
        return get_staff_ca_menu_keyboard()
    if role == UserRole.COORDINATOR_RO:
        return get_coordinator_ro_menu_keyboard()
    if role == UserRole.STAFF_RO:
        return get_staff_ro_menu_keyboard()
    if role == UserRole.HEADLINER:
        return get_headliner_menu_keyboard()
    return get_user_menu_keyboard()


def get_role_menu_keyboard(role: UserRole | None) -> InlineKeyboardBuilder:
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
