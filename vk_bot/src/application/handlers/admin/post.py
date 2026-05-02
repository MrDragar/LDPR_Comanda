import asyncio
from vkbottle.bot import BotLabeler, Message
from src.application.states import PostsStates
from src.application.filters import AdminFilter
from src.services.interfaces import IUserService

router = BotLabeler()
router.auto_rules = [AdminFilter()]


@router.message(text="/post")
async def cmd_post(message: Message):
    await message.state_dispenser.set(message.from_id, PostsStates.GET_MESSAGE)
    await message.answer(
        "Отправьте сообщение (текст), которое нужно разослать всем пользователям:")


@router.message(state=PostsStates.GET_MESSAGE)
async def confirm_post(message: Message):
    await message.state_dispenser.set(message.from_id, PostsStates.CONFIRM,
                                      msg_text=message.text)
    await message.answer(
        f"Вы уверены, что хотите разослать это сообщение?\n\n{message.text}\n\nОтправьте 'Да' для подтверждения.")


@router.message(state=PostsStates.CONFIRM, text="Да")
async def start_mailing(message: Message, user_service: IUserService):
    state = await message.state_dispenser.get(message.from_id)
    msg_text = state.payload['msg_text']
    users = await user_service.get_all_users()

    await message.answer(f"Начинаю рассылку на {len(users)} пользователей...")

    count = 0
    for u in users:
        try:
            await message.ctx_api.messages.send(peer_id=u.id, message=msg_text,
                                                random_id=0)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.state_dispenser.delete(message.from_id)
    await message.answer(f"Рассылка завершена. Успешно отправлено: {count}")
