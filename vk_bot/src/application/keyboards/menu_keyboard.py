from vkbottle import Keyboard, Text


def get_menu_keyboard():
    return (Keyboard(one_time=False).add(Text("Личный кабинет")).
            add(Text("Сгенерировать аватарку")).get_json())
