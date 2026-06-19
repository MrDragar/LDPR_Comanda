from vkbottle import Keyboard, Callback, OpenLink

def get_personal_data_keyboard():
    return (Keyboard(inline=True)
            .add(Callback("Согласиться", {"cmd": "pd_agree"}))
            .row()
            .add(OpenLink(
                "https://командалдпр.рф/privacypolitic",
                "Политика конфиденциальности"
            ))
            .get_json())
