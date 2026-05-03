from vkbottle import PhotoMessageUploader
from vkbottle.bot import BotLabeler, Message
from vkbottle.tools.formatting import Formatter

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.domain.entities import Sources
from src.services.interfaces import IReferralService, IParticipationService
from src.services.referral_link_service import ReferralLinkService

router = BotLabeler()


@router.message(text=['Посмотреть свои номера'])
async def show_numbers(
        message: Message,
        participation_service: IParticipationService
):
    if message.peer_id <= 0:
        return
    numbers = await participation_service.get_all_participation_ids(
        message.peer_id, Sources.VK
    )

    res = ['Ваши номера:\n', *list(map(str, numbers[:100]))]
    if len(numbers) > 100:
        res.append('...')
    await message.reply(
        '\n'.join(res)
    )
    await message.answer("Меню", keyboard=get_menu_keyboard())


@router.message(text=['Реферальная ссылка'])
async def generate_referral(
        message: Message,
        referral_service: IReferralService,
        referral_link_service: ReferralLinkService,
        photo_uploader: PhotoMessageUploader
):
    if message.peer_id <= 0:
        return
    referral_count = await referral_service.get_count_invitees(
        message.peer_id, Sources.TG
    )
    await message.answer(
        f"Вы пригласили уже {referral_count} людей\n"
        "Пригласи трёх друзей к участию в розыгрыше и получи дополнительные номера для "
        "увеличения шансов выигрыша"
    )
    post = referral_link_service.generate_post(message.peer_id)

    photo = await photo_uploader.upload(post.image_path, peer_id=message.peer_id)
    await message.answer(
        post.text,
        attachment=photo
    )
    await message.answer("Меню", keyboard=get_menu_keyboard())
