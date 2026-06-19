import logging

from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import Sources
from src.services.interfaces import IHeadlinerService, IUserService

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
        headliner_service: IHeadlinerService | None = None,
):
    try:
        if await user_service.is_user_exists(peer_id):
            await ctx_api.messages.send(
                peer_id=peer_id,
                message="Вы уже зарегистрированы в системе.",
                random_id=0,
            )
            await state_dispenser.delete(peer_id)
            return

        user = await user_service.create_user(
            user_id=peer_id,
            username=None,
            surname=state_payload["surname"],
            name=state_payload["name"],
            is_member=state_payload["is_member"],
            patronymic=state_payload.get("patronymic"),
            birth_date=state_payload["birth_date"],
            phone_number=state_payload["phone"],
            region=state_payload["region"],
            email=state_payload["email"],
            gender=state_payload["gender"],
            city=state_payload["city"],
            wish_to_join=state_payload.get("wish_to_join", False),
            home_address=state_payload.get("home_address"),
            news_subscription=state_payload["news_subscription"],
        )

        referral_headliner = None
        headliner_id = state_payload.get("headliner_id")
        if headliner_id is not None and headliner_service is not None:
            await headliner_service.attach_follower(int(headliner_id), user.id, Sources.VK)
            referral_headliner = await headliner_service.get_by_id(int(headliner_id))

        try:
            photo = await photo_uploader.upload("docs/sokol_like.webp", peer_id=peer_id)
            await ctx_api.messages.send(peer_id=peer_id, attachment=photo, random_id=0)
        except Exception:
            ...

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Поздравляем!\nВы успешно зарегистрированы.",
            random_id=0,
        )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Приглашай друзей и получи 10 баллов за приглашённого пользователя.",
            random_id=0,
        )

        if referral_headliner and referral_headliner.welcome_message:
            await ctx_api.messages.send(
                peer_id=peer_id,
                message=(
                    f"Сообщение от хэдлайнера {referral_headliner.fio}:\n\n"
                    f"{referral_headliner.welcome_message}"
                ),
                random_id=0,
            )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Меню",
            keyboard=get_role_menu_keyboard(user.role),
            random_id=0,
        )

        log_text = (
            "Новый пользователь зарегистрировался\n"
            "Источник: ВК\n"
            f"Является членом партии: {'Да' if user.is_member else 'Нет'}\n"
            f"ФИО: {user.surname} {user.name} {user.patronymic or ''}\n"
            f"Пол: {user.gender}\n"
            f"Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            f"Почта: {user.email}\n"
            f"Номер телефона: {user.phone_number}\n"
            f"Регион: {user.region}\n"
            f"Город: {user.city}\n"
            f"Хочет вступить в партию ЛДПР: {'Да' if user.wish_to_join else 'Нет'}\n"
            f"Домашний адрес: {user.home_address or ''}\n"
            f"Подписка на новости: {'Есть' if user.news_subscription else 'Нет'}\n\n"
            f"ID участника: {user.id}\n"
        )

        await tg_bot.send_message(chat_id=log_chat, text=log_text)

    except Exception as e:
        logger.error(f"Error in finish_registration: {e}")
        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.",
            random_id=0,
        )
