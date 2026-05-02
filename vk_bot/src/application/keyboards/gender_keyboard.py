from vkbottle import Keyboard, Text

def get_gender_keyboard():
    return Keyboard(one_time=True).add(Text("Мужской")).add(Text("Женский")).get_json()