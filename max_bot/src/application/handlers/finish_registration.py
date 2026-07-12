import logging
from aiogram import Bot as TgBot
from maxapi.types import MessageCreated, InputMedia
from maxapi.context import MemoryContext
from maxapi import Bot
from src.services.interfaces import IUserService, IHeadlinerService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources

logger = logging.getLogger(__name__)


async def finish_registration(
        event: MessageCreated, context: MemoryContext, bot: Bot,
        user_service: IUserService, tg_bot: TgBot, log_chat: str, group_link: str,
        headliner_service: IHeadlinerService
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
            email=state_data.get('email'),
            gender=state_data.get('gender'),
            city=state_data.get('city'),
            wish_to_join=state_data.get('wish_to_join', False),
            is_member=state_data.get('is_member', False),
            home_address=state_data.get('home_address'),
            news_subscription=state_data.get('news_subscription', False),
            birth_date=state_data.get('birth_date', None)
        )

        referral_headliner = None
        headliner_id = state_data.get("headliner_id")
        if headliner_id is not None and headliner_service is not None:
            try:
                await headliner_service.attach_follower(int(headliner_id), user.id, user.source)
                referral_headliner = await headliner_service.get_by_id(int(headliner_id))
            except Exception as e:
                logging.debug(f"Got Exception {e}")

        try:
            media = InputMedia("docs/sokol_like.webp")
            attachment = await bot.upload_media(media)
            await event.message.answer(attachments=[attachment])
        except Exception as e:
            logger.error(f"Media upload error: {e}")

        await event.message.answer("Поздравляем, вы успешно зарегистрированы.")
        await event.message.answer(
            "Приглашай друзей и получай 10 баллов за приглашённого пользователя.")

        if referral_headliner is not None and referral_headliner.welcome_message:
            await event.message.answer(
                f"Сообщение от хедлайнера {referral_headliner.fio}:\n"
                f"{referral_headliner.welcome_message}"
            )
        await event.message.answer(
            f"Вы присоединились к Большой команде ЛДПР.\nВаше звание — Сторонник."
        )
        await event.message.answer(
            "Отправьте заявку на вступление в нашу закрытую группу, чтобы стать частью нашей большой команды\n"
            f"{group_link}"
        )

        await event.message.answer("Меню",
                                   attachments=[get_role_menu_keyboard(user.role).as_markup()])

        log_text = (
            f"Новый пользователь зарегистрировался\n"
            f"Источник: MAX\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Пол: {user.gender or 'не указан'}\n"
            f"Дата рождения: {user.birth_date.strftime('%d.%m.%Y') if user.birth_date else 'не указана'}\n"
            f"Почта: {user.email or 'не указана'}\n"
            f"Номер телефона: {user.phone_number}\n"
            f"Регион: {user.region}\n"
            f"Город: {user.city or 'не указан'}\n"
            f"Хочет вступить в партию ЛДПР: {'Да' if user.wish_to_join else 'Нет'}\n"
            f"Домашний адрес: {user.home_address or 'не указан'}\n"
            f"Подписка на новости: {'Есть' if user.news_subscription else 'Нет'}\n"
            f"ID участника: {user.id}\n"
            f"Хедлайнер: {referral_headliner.fio if referral_headliner else 'Нет'}\n"
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
