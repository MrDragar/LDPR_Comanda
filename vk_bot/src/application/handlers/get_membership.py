from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.MEMBERSHIP)
async def get_membership(message: Message,
                         state_dispenser: BuiltinStateDispenser):
    text = message.text.lower().strip() if message.text else ""

    if text not in ['РґР°', 'РЅРµС‚']:
        await message.answer("РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІС‹Р±РµСЂРёС‚Рµ РІР°СЂРёР°РЅС‚ РЅР° РєР»Р°РІРёР°С‚СѓСЂРµ:",
                             keyboard=get_boolean_keyboard())
        return

    is_member = (text == 'РґР°')
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id,
                              RegistrationStates.SURNAME,
                              **state.payload,
                              is_member=is_member)
    await message.answer("Р’РІРµРґРёС‚Рµ РІР°С€Сѓ С„Р°РјРёР»РёСЋ:")
