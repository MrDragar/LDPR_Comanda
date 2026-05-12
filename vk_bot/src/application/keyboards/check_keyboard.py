from vkbottle import Keyboard, Text


def get_check_keyboard():
    return Keyboard(one_time=True).add(Text("Проверить")).get_json()
