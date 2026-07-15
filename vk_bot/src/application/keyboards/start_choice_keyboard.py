from vkbottle import Keyboard, Callback, VKApps

vk_app = VKApps(app_id=54510502, owner_id=200072379, label="Регистрация через приложение")


def get_start_choice_keyboard() -> str:
    kb = Keyboard(inline=True)
    kb.add(vk_app).row()
    kb.add(Callback("Регистрация через бота", {"cmd": "start_text_reg"}))
    kb.row()
    return kb.get_json()
