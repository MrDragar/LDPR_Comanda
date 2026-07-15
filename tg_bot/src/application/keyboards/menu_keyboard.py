from aiogram.types import ReplyKeyboardMarkup, WebAppInfo, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from src.domain.entities.user import UserRole


WEBAPP_URL = "https://миниапп.командалдпр.рф/app"
web_app_info = WebAppInfo(url=WEBAPP_URL)


def get_miniapp_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Запустить", web_app=web_app_info))
    builder.add(InlineKeyboardButton(text="Назад"))
    builder.adjust(1, 1)
    return builder.as_markup()


def get_headliner_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="Открыть приложение")
    builder.button(text="Личный кабинет")
    builder.button(text="Приветственное сообщение")
    builder.button(text="Рейтинг хедлайнеров")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_role_menu_keyboard(role: UserRole | None) -> ReplyKeyboardMarkup:
    """Генерирует главное меню в зависимости от роли пользователя (1 в 1 как в ВК)."""
    if role == UserRole.HEADLINER:
        return get_headliner_menu_keyboard()
    builder = ReplyKeyboardBuilder()

    # Базовые пользовательские кнопки
    if role in [UserRole.USER, UserRole.CANDIDATE]:
        builder.button(text="Открыть приложение", web_app=web_app_info)
        builder.button(text="Поручения штаба")
        builder.button(text="Действующие поручения")
        builder.button(text="Личный кабинет")
        builder.button(text="Реферальная ссылка")
        builder.button(text="Обучение")
        # builder.button(text="Магазин")
        builder.button(text="Закрытые мероприятия")
        builder.adjust(1, 2, 2, 1, 1)

    # Кнопки для сотрудников РО, координаторов и ЦА
    if role in (UserRole.STAFF_RO, UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.button(text="Открыть приложение", web_app=web_app_info)
        builder.button(text="Проверить офлайн задачи")
        builder.button(text="Управление заказами")
        builder.button(text="Список участников мероприятия")
        builder.adjust(1, 1, 1, 1)

    # Кнопки для координаторов РО и ЦА
    if role in (UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        builder.button(text="Создать офлайн задачу")
        builder.button(text="Управление пользователями")
        builder.button(text="Создать закрытое мероприятие")
        builder.adjust(1, 1, 1, )

    # Кнопки только для сотрудников ЦА
    if role == UserRole.STAFF_CA:
        builder.button(text="Создать онлайн задачу")
        builder.button(text="Добавить товар")
        builder.button(text="Скрыть товар")
        builder.button(text="Рассылка координаторам РО")
        builder.adjust(1, 1, 2)

    return builder.as_markup(resize_keyboard=True)