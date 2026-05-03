from vkbottle import Keyboard, Text


def get_menu_keyboard():
    return Keyboard(one_time=False).add(Text("Реферальная ссылка")).add(Text("Посмотреть свои номера")).get_json()
