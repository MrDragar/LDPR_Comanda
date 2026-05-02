from vkbottle import Keyboard, Text

def get_boolean_keyboard():
    return Keyboard(one_time=True).add(Text("Да")).add(Text("Нет")).get_json()