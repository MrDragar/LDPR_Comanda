import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text
from src.services.interfaces import IUserService, IReferralService, IBalanceService
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = BotLabeler()


@router.message(text=["Личный кабинет"])
async def profile(message: Message, user_service: IUserService, referral_service: IReferralService,
                  balance_service: IBalanceService):
    try:
        u = await user_service.get_user(message.from_id, Sources.VK)
        balance = await balance_service.get_balance(u.id, u.source)
        refs = await referral_service.get_count_invitees(u.id, u.source)
        on_count = await user_service.get_completed_tasks_count(u.id, u.source, True)
        off_count = await user_service.get_completed_tasks_count(u.id, u.source, False)

        text = (f"👤 {u.surname} {u.name}\n"
                f"Роль: {u.role.value}\n"
                f"Баланс: {balance} баллов\n"
                f"Рефералов: {refs}\n"
                f"Выполнено онлайн: {on_count}\n"
                f"Выполнено оффлайн: {off_count}")
        kb = Keyboard(one_time=True).add(Text("Вернуться на главную страницу"))
        await message.answer(text, keyboard=kb.get_json())
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await message.answer("Ошибка загрузки профиля")
