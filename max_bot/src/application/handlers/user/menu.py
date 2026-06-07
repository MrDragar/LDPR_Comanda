from maxapi import Router, F
from maxapi.types import MessageCreated
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources
from src.services.interfaces import IUserService

router = Router()


@router.message_created(F.message.body.text.lower().in_(["меню", "на главную", "вернуться на главную страницу"]))
async def show_menu(event: MessageCreated, user_service: IUserService):
    try: role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    except Exception: role = None
    if role:
        await event.message.answer("Главное меню:", attachments=[get_role_menu_keyboard(role).as_markup()])
    else:
        return await event.message.answer("Вы не зарегистрированы")
