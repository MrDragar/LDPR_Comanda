import logging
from maxapi import Router, F, Bot
from maxapi.enums import ParseMode
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import PostsStates
from src.services.interfaces import IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = Router()


@router.message_created(F.message.body.text.in_(["/post", "Рассылка всем"]))
async def cmd_post(event: MessageCreated, context: MemoryContext, admin_ids: list[int]):
    # Проверка прав администратора
    if str(event.from_user.user_id) not in [str(i) for i in admin_ids]:
        return await event.message.answer("Недостаточно прав.")

    await event.message.answer(
        "Отправьте сообщение (текст, фото, видео или документ), которое нужно разослать всем пользователям:"
    )
    await context.set_state(PostsStates.get_message)


@router.message_created(PostsStates.get_message)
async def get_message(event: MessageCreated, context: MemoryContext):
    # Сохраняем ID чата (peer_id) и ID самого сообщения для последующего получения через API
    await context.update_data(
        message_id=event.message.body.mid
    )
    await event.message.answer(
        "Сообщение сохранено. Подтвердите начало рассылки. (Подтвердить / Отменить)")
    await context.set_state(PostsStates.confirm)


@router.message_created(PostsStates.confirm, F.message.body.text == "Подтвердить")
async def confirm_post(event: MessageCreated, context: MemoryContext, user_service: IUserService,
                       bot: Bot):
    if await context.get_state() != PostsStates.confirm:
        return

    data = await context.get_data()
    message_id = data.get('message_id')

    users = await user_service.get_all_users()
    await event.message.answer(f"Начинаю рассылку на {len(users)} пользователей...")

    success_count = 0

    try:
        # Получаем исходный объект сообщения через API бота
        msg = await bot.get_message(message_id=message_id)
    except Exception as e:
        logger.error(f"Failed to get message: {e}")
        await event.message.answer("Не удалось получить исходное сообщение для рассылки.")
        await context.clear()
        return

    for user in users:
        try:
            await bot.send_message(
                chat_id=None, user_id=user.id, text=msg.body.md_text, 
                attachments=msg.body.attachments, parse_mode=ParseMode.MARKDOWN
           )
            # await msg.forward(user_id=user.id, chat_id=None)
            success_count += 1
        except Exception as e:
            logger.debug(f"Failed to forward to {user.id}: {e}")

    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer(
        f"Рассылка завершена. Успешно отправлено: {success_count} из {len(users)}")
    await event.message.answer("Главное меню:",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(PostsStates.confirm, F.message.body.text == "Отменить")
async def cancel_post(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if await context.get_state() != PostsStates.confirm:
        return
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Рассылка отменена.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])