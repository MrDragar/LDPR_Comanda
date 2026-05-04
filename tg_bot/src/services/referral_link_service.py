from src.domain.entities import Repost
from src.domain.entities.user import Sources
from src.services.interfaces import IReferralLinkService


class ReferralLinkService(IReferralLinkService):
    def __init__(self, vk_bot_link: str, tg_bot_link: str, source: Sources, image_path: str):
        self.vk_bot_link = vk_bot_link
        self.tg_bot_link = tg_bot_link
        self.source = source
        self.image_path = image_path

    def generate_post(self, user_id: int) -> Repost:
        vk_url = f"{self.vk_bot_link}?ref={user_id}_{self.source.value}"
        tg_url = f"{self.tg_bot_link}?start={user_id}_{self.source.value}"

        text = (
            "<b>🔥 Грандиозный конкурс от ЛДПР!</b>\n\n"
            "Участвуй и выигрывай крутые призы!\n"
            "Присоединяйся прямо сейчас и приглашай друзей:\n\n"
            f"ВКонтакте: <a href='{vk_url}'>Перейти в бота ВК</a>\n"
            f"Telegram: <a href='{tg_url}'>Перейти в бота TG</a>\n\n"
            "<i>Твое будущее в твоих руках!</i>"
        )

        return Repost(text=text, image_path=self.image_path)
