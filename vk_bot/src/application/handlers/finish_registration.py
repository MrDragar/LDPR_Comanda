import logging

from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.handlers.auth_confirmation import request_auth_confirmation
from src.application.states import RegistrationStates
from src.domain.entities.user import Sources
from src.services.interfaces import IHeadlinerService, INotificationService, IUserService

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
        headliner_service: IHeadlinerService | None
):
    if headliner_service is None:
        return user.role

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
        user_service: IUserService,
        peer_id: int,
        state_payload: dict,
        ctx_api,
        log_chat: str,
        state_dispenser,
        tg_bot: TgBot,
        photo_uploader: PhotoMessageUploader,
        notification_service: INotificationService,
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

        if await request_auth_confirmation(
                user_service,
                notification_service,
                peer_id,
                Sources.VK,
                {**state_payload, "username": None, "phone": state_payload.get("phone")}
        ):
            await ctx_api.messages.send(
                peer_id=peer_id,
                message=(
                    "Профиль с такими ФИО и телефоном уже есть на другой площадке.\n"
                    "Мы отправили код на первый зарегистрированный профиль. Введите его здесь."
                ),
                random_id=0,
            )
            await state_dispenser.set(peer_id, RegistrationStates.AUTH_CODE, **state_payload)
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

        user_role = await sync_headliner_role(user, Sources.VK, user_service, headliner_service)

        referral_headliner = None
        headliner_id = state_payload.get("headliner_id")
        if headliner_id is not None and headliner_service is not None:
            try:
                await headliner_service.attach_follower(int(headliner_id), user.id, Sources.VK)
                referral_headliner = await headliner_service.get_by_id(int(headliner_id))
            except Exception as e:
                logger.error(e)
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
                    f"Сообщение от хедлайнера {referral_headliner.fio}:\n\n"
                    f"{referral_headliner.welcome_message}"
                ),
                random_id=0,
            )

        await ctx_api.messages.send(
            peer_id=peer_id,
            message="Меню",
            keyboard=get_role_menu_keyboard(user_role),
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
