from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton, MessageButton

# ЗАМЕНИТЕ НА ССЫЛКУ НА ВАШ MINI APP
MINI_APP_URL = "https://командалдпр.рф/app"


def get_start_choice_keyboard() -> list:
    builder = InlineKeyboardBuilder()
    # Кнопка для продолжения текстовой регистрации (отправит callback)
    builder.row(CallbackButton(text="📝 Регистрация в боте", payload="start_text_reg"))
    # Кнопка для открытия Mini App (откроет ссылку)
    builder.row(MessageButton(text="📱 Открыть Mini App", url=MINI_APP_URL))
    return [builder.as_markup()]
