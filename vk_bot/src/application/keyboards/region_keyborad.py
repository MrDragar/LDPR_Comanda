from vkbottle import Keyboard, Callback


def get_region_keyboard(regions: list[str]):
    kb = Keyboard(inline=True)
    for r in regions[:5]:
        kb.add(Callback(r[:40], {"cmd": "region", "region": r}))
        kb.row()
    kb.add(Callback("Ввести заново", {"cmd": "retry_reg"}))
    return kb.get_json()
