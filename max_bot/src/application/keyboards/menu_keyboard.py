from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.domain.entities.user import UserRole


def get_headliner_menu_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Личный кабинет"))
    builder.row(MessageButton(text="Приветственное сообщение"))
    builder.row(MessageButton(text="Рейтинг хедлайнеров"))
    return builder


def get_role_menu_keyboard(role: UserRole | None) -> InlineKeyboardBuilder:
    if role == UserRole.HEADLINER:
        return get_headliner_menu_keyboard()
    builder = InlineKeyboardBuilder()
    if role == UserRole.USER:
        builder.row(MessageButton(text="Выполнить действие"))
        builder.row(MessageButton(text="Мои действия"))
        builder.row(MessageButton(text="Личный кабинет"))
        builder.row(MessageButton(text="Обучение"), MessageButton(text="Реферальная ссылка"))
        # builder.row(MessageButton(text="Магазин"))
        builder.row(MessageButton(text="Закрытые мероприятия"))

    if role in (UserRole.STAFF_RO, UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.row(MessageButton(text="Проверить офлайн задачи"))
        builder.row(MessageButton(text="Управление заказами"))
        builder.row(MessageButton(text="Список участников мероприятия"))

    if role in (UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.row(MessageButton(text="Создать офлайн задачу"))
        builder.row(MessageButton(text="Управление пользователями"))
        builder.row(MessageButton(text="Создать закрытое мероприятие"))

    if role == UserRole.STAFF_CA:
        builder.row(MessageButton(text="Создать онлайн задачу"))
        builder.row(MessageButton(text="Добавить товар"))
        builder.row(MessageButton(text="Скрыть товар"))
        builder.row(MessageButton(text="Рассылка координаторам РО"))

    return builder
