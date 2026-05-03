import logging

from aiogram import Router, types, F
from aiogram.types import FSInputFile

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.domain.entities import Sources
from src.services.interfaces import IParticipationService, IReferralService
from src.services.referral_link_service import ReferralLinkService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(F.text == 'Посмотреть свои номера')
async def show_numbers(
        message: types.Message,
        participation_service: IParticipationService,
):
    numbers = await participation_service.get_all_participation_ids(
        message.from_user.id, Sources.TG
    )

    res = ['Ваши номера:\n', *list(map(str, numbers[:100]))]
    if len(numbers) > 100:
        res.append('...')
    await message.reply(
        '\n'.join(res)
    )
    await message.answer("Меню", reply_markup=get_menu_keyboard())
    
    
@router.message(F.text == 'Реферальная ссылка')
async def generate_referral(
        message: types.Message,
        referral_service: IReferralService,
        referral_link_service: ReferralLinkService
):
    referral_count = await referral_service.get_count_invitees(
        message.from_user.id, Sources.TG
    )
    await message.answer(
        f"Вы пригласили уже {referral_count} людей\n"
        "Пригласи трёх друзей к участию в розыгрыше и получи дополнительные номера для "
        "увеличения шансов выигрыша"
    )
    post = referral_link_service.generate_post(message.from_user.id)
    photo = await message.reply_photo(
        FSInputFile(post.image_path),
        caption=post.text,
        parse_mode='HTML'
    )
    logger.debug(F"Sent photo: {photo}")
    await message.answer("Меню", reply_markup=get_menu_keyboard())