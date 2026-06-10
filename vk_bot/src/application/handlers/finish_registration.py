import logging
from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader

from src.services.interfaces import IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

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
            name=state_payload.get('name'),
            patronymic=state_payload.get('patronymic'),
            phone_number=state_payload.get('phone'),
            birth_date=state_payload.get('birth_date'),
            region=state_payload.get('region'),
            news_subscription=state_payload.get('news_subscription', False)
        )
        try:
            photo = await photo_uploader.upload(
                'docs/sokol_like.webp',
                peer_id=peer_id
            )
            await ctx_api.messages.send(
                peer_id=peer_id,
                attachment=photo,
                random_id=0
            )
        except:
            ...

        await ctx_api.messages.send(
            peer_id=peer_id,
            message=(
                f"Поздравляем!\nВы успешно зарегистрированы.\n"
            ),
            random_id=0
        )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Меню",
            keyboard=get_role_menu_keyboard(user.role),
            random_id=0
        )
        log_text = (
            f"Новый пользователь зарегистрировался\n"
            f"Источник: ВК\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            f"Номер телефона: {user.phone_number}\n"
            f"Регион: {user.region}\n"
            f"Подписка на новости: {'Есть' if user.news_subscription else 'Нет'}\n\n"
            
            f"ID участника: {user.id}\n"
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
