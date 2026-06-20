import logging
from aiogram import Bot as TgBot
from maxapi.types import MessageCreated, InputMedia
from maxapi.context import MemoryContext
from maxapi import Bot
from src.services.interfaces import IHeadlinerService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources

logger = logging.getLogger(__name__)


def normalize_fio(surname: str, name: str | None, patronymic: str | None) -> str:
    parts = [surname, name, patronymic]
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def normalize_phone(phone_number: str | None) -> str:
    return "".join(symbol for symbol in (phone_number or "") if symbol.isdigit())


async def sync_headliner_role(
        user,
        source: Sources,
        user_service: IUserService,
        headliner_service: IHeadlinerService
):
    existing = await headliner_service.get_by_user(user.id, source)
    if existing is not None:
        return await user_service.get_user_role(user.id, source)

    user_fio = normalize_fio(user.surname, user.name, user.patronymic)
    user_phone = normalize_phone(user.phone_number)
    for headliner in await headliner_service.get_all():
        try:
            headliner_user = await user_service.get_user(headliner.user_id, headliner.user_source)
        except Exception:
            continue

        if normalize_phone(headliner_user.phone_number) != user_phone:
            continue
        if normalize_fio(headliner_user.surname, headliner_user.name, headliner_user.patronymic) != user_fio:
            continue

        await headliner_service.create_headliner(
            user_id=user.id,
            user_source=source,
            fio=headliner.fio,
            position=headliner.position,
            topic=headliner.topic,
            group_link=headliner.group_link,
            photo=headliner.photo,
        )
        if headliner.welcome_message:
            await headliner_service.update_welcome_message_by_user(
                user.id,
                source,
                headliner.welcome_message
            )
        return await user_service.get_user_role(user.id, source)

    return user.role


async def finish_registration(
        event: MessageCreated,
        context: MemoryContext,
        bot: Bot,
        user_service: IUserService,
        headliner_service: IHeadlinerService,
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
            news_subscription=state_data.get('news_subscription', False),
            birth_date=state_data.get('birth_date', None)
        )

        user_role = await sync_headliner_role(user, Sources.MAX, user_service, headliner_service)

        try:
            media = InputMedia("docs/sokol_like.webp")
            attachment = await bot.upload_media(media)
            await event.message.answer(attachments=[attachment])
        except Exception as e:
            logger.error(f"Media upload error: {e}")

        await event.message.answer(f"Поздравляем!\nВы успешно зарегистрированы.\n")
        pending_headliner_id = state_data.get("pending_headliner_id")
        if pending_headliner_id:
            follower = await headliner_service.attach_follower(
                pending_headliner_id,
                peer_id,
                Sources.MAX
            )
            headliner = await headliner_service.get_by_id(pending_headliner_id)
            if follower and headliner and headliner.welcome_message:
                await event.message.answer(headliner.welcome_message)

        await event.message.answer("Меню",
                                   attachments=[get_role_menu_keyboard(user_role).as_markup()])

        log_text = (
            f"Новый пользователь зарегистрировался\n"
            f"Источник: MAX\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
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
