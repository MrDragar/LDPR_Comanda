from vkbottle import Keyboard, Callback

def get_personal_data_keyboard():
    return (Keyboard(inline=True)
            .add(Callback("Согласиться", {"cmd": "pd_agree"}))
            .add(Callback("Отказаться", {"cmd": "pd_disagree"}))
            .row()
            .add(Callback("Условия", {"cmd": "pd_read"}))
            .get_json())