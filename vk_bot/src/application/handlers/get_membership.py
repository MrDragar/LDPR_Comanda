from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.MEMBERSHIP)
async def get_membership(message: Message,
                         state_dispenser: BuiltinStateDispenser):
    text = message.text.lower().strip() if message.text else ""

    if text not in ['да', 'нет']:
        await message.answer("Пожалуйста, выберите вариант на клавиатуре:",
                             keyboard=get_boolean_keyboard())
        return

    is_member = (text == 'да')
    await state_dispenser.set(message.from_id,
                              RegistrationStates.SURNAME,
                              is_member=is_member)
    await message.answer("Введите вашу фамилию:")
