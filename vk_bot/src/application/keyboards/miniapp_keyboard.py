from vkbottle import Keyboard, OpenLink


def get_miniapp_keyboard():
    return Keyboard(inline=True).add(OpenLink("https://ldpr.ru/", "Открыть сайт")).get_json()
