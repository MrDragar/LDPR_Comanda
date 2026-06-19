from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from src.domain.entities.user import UserRole


def get_role_menu_keyboard(role: UserRole | None) -> ReplyKeyboardMarkup:
    """Генерирует главное меню в зависимости от роли пользователя (1 в 1 как в ВК)."""
    builder = ReplyKeyboardBuilder()

    # Базовые пользовательские кнопки
    builder.button(text="Выполнить задание")
    builder.button(text="Мои задания")
    builder.button(text="Личный кабинет")
    builder.button(text="Обучение")
    builder.button(text="Магазин")
    builder.button(text="Закрытые мероприятия")

    # Кнопки для сотрудников РО, координаторов и ЦА
    if role in (UserRole.STAFF_RO, UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.button(text="Проверить офлайн задачи")
        builder.button(text="Управление заказами")
        builder.button(text="Список участников мероприятия")

    # Кнопки для координаторов РО и ЦА
    if role in (UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.button(text="Создать офлайн задачу")
        builder.button(text="Управление пользователями")
        builder.button(text="Создать закрытое мероприятие")

    # Кнопки только для сотрудников ЦА
    if role == UserRole.STAFF_CA:
        builder.button(text="Создать онлайн задачу")
        builder.button(text="Добавить товар")
        builder.button(text="Скрыть товар")
        builder.button(text="Рассылка координаторам РО")

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)