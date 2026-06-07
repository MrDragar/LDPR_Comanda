import logging
from aiogram import Bot as TgBot
from maxapi.types import MessageCreated, InputMedia
from maxapi.context import MemoryContext
from maxapi import Bot
from src.services.interfaces import IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources

logger = logging.getLogger(__name__)


async def finish_registration(
        event: MessageCreated,
        context: MemoryContext,
        bot: Bot,
        user_service: IUserService,
        tg_bot: TgBot,
        log_chat: str
):
    peer_id = event.from_user.user_id
    state_data = await context.get_data()
    try:
        if await user_service.is_user_exists(peer_id, Sources.MAX):
            await event.message.answer("Вы уже зарегистрированы в системе.")
            return await context.clear()

        user = await user_service.create_user(
            user_id=peer_id,
            username=event.from_user.username if hasattr(event.from_user, 'username') else None,
            surname=state_data['surname'],
            name=state_data.get('name'),
            patronymic=state_data.get('patronymic'),
            phone_number=state_data.get('phone'),
            region=state_data.get('region'),
            news_subscription=state_data.get('news_subscription', False)
        )

        # Отправка приветственной картинки
        try:
            media = InputMedia("docs/sokol_like.webp")
            attachment = await bot.upload_media(media)
            await event.message.answer(attachments=[attachment])
        except Exception as e:
            logger.error(f"Media upload error: {e}")

        await event.message.answer(f"Поздравляем!\nВы успешно зарегистрированы.\n")
        await event.message.answer("Меню",
                                   attachments=[get_role_menu_keyboard(user.role).as_markup()])

        # === ЛОГИРОВАНИЕ В TELEGRAM ===
        log_text = (
            f"Новый пользователь зарегистрировался\n"
            f"Источник: MAX\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Номер телефона: {user.phone_number}\n"
            f"Регион: {user.region}\n"
            f"Подписка на новости: {'Есть' if user.news_subscription else 'Нет'}\n"
            f"ID участника: {user.id}\n"
        )
        try:
            await tg_bot.send_message(chat_id=log_chat, text=log_text)
        except Exception as e:
            logger.error(f"Failed to send log to TG: {e}")

    except Exception as e:
        logger.error(f"Error in finish_registration: {e}", exc_info=True)
        await event.message.answer(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
    finally:
        await context.clear()