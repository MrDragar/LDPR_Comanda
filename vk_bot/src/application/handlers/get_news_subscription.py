from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.check_keyboard import get_check_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.NEWS_SUBSCRIPTION)
async def get_news_sub(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        group_id: int
):
    text = message.text.lower().strip() if message.text else ""
    if text not in ['да', 'нет']:
        await message.answer("Хотели бы вы получать новости? (Да/Нет)")
        return
    state = await state_dispenser.get(message.from_id)
    new_payload = {**state.payload, 'news_subscription': text == 'да'}
    await state_dispenser.set(
        message.from_id,
        RegistrationStates.CHECK_SUBSCRIPTION,
        **new_payload
    )
    await message.answer(
        "Для завершения регистрации подпишитесь на сообщество Большой команды ЛДПР"
        f"https://vk.com/club{group_id}\n"
    )
    await message.answer('Нажмите кнопку "Проверить", когда отправите заявку на '
                         'вступление в сообщество. Бот автоматически её одобрит',
                         keyboard=get_check_keyboard())