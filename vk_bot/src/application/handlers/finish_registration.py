import logging
from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader

from src.application.keyboards.miniapp_keyboard import get_miniapp_keyboard
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)


async def finish_registration(
        user_service: IUserService,
        peer_id: int,
        state_payload: dict,
        ctx_api,
        log_chat: str,
        state_dispenser,
        tg_bot: TgBot,
        photo_uploader: PhotoMessageUploader,
):
    """
    Завершает процесс регистрации: сохраняет пользователя в БД, 
    отправляет уведомления и переводит стейт в подписку на новости.
    """
    try:
        # Проверка на дубликат перед созданием
        if await user_service.is_user_exists(peer_id):
            await ctx_api.messages.send(
                peer_id=peer_id,
                message="Вы уже зарегистрированы в системе.",
                random_id=0
            )
            await state_dispenser.delete(peer_id)
            return

        user = await user_service.create_user(
            user_id=peer_id,
            username=None,
            surname=state_payload['surname'],
            name=state_payload['name'],
            is_member=state_payload['is_member'],
            patronymic=state_payload.get('patronymic'),
            birth_date=state_payload['birth_date'],
            phone_number=state_payload['phone'],
            region=state_payload['region'],
            email=state_payload['email'],
            gender=state_payload['gender'],
            city=state_payload['city'],
            wish_to_join=state_payload.get('wish_to_join', False),
            home_address=state_payload.get('home_address'),
            news_subscription=state_payload['news_subscription']
        )

        photo = await photo_uploader.upload(
            'docs/sokol_like.webp',
            peer_id=peer_id
        )
        await ctx_api.messages.send(
            peer_id=peer_id,
            attachment=photo,
            random_id=0
        )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message=(
                f"Поздравляем, вы успешно зарегистрированы.\n"
                f"Ваш уникальный номер — Б{user.id}."
            ),
            random_id=0
        )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Используйте кнопку ниже, чтобы открыть наш сайт",
            keyboard=get_miniapp_keyboard(),
            random_id=0
        )

        log_text = (
            f"Новый пользователь зарегистрировался\n"
            f"Источник: ВК\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Пол: {user.gender}\n"
            f"Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            f"Почта: {user.email}\n"
            f"Номер телефона: {user.phone_number}\n"
            f"Регион: {user.region}\n"
            f"Город: {user.city}\n"
            f"Хочет присоединиться к команде ЛДПР: {'Да' if user.wish_to_join else 'Нет'}\n"
            f"Домашний адрес: {user.home_address or ''}\n"
            f"Подписка на новости: {'Есть' if user.news_subscription else 'Нет'}\n\n"
            
            f"Номер участника: Б{user.id}"
        )

        await tg_bot.send_message(
            chat_id=log_chat,
            text=log_text,
        )

    except Exception as e:
        logger.error(f"Error in finish_registration: {e}")
        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.",
            random_id=0
        )
