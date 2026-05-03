from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.application.states import ParticipateRegisteredStates
from src.domain.entities import Sources
from src.services.interfaces import IParticipationService

router = Router()


@router.message(ParticipateRegisteredStates.step, F.text == 'Да')
async def take_a_part(
        message: types.Message, state: FSMContext,
        participation_service: IParticipationService,
):
    number = await participation_service.activate_participation(message.from_user.id, Sources.TG)
    await message.reply(
        f"Поздравляем, Вы успешно зарегистрированы в нашем конкурсе.\n"
        f"Ваш уникальный номер - {number}."
    )
    await state.clear()
    await message.answer("Меню", reply_markup=get_menu_keyboard())