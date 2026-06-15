from src.domain.entities import Repost
from src.domain.entities.user import Sources
from src.services.interfaces import IReferralLinkService


class ReferralLinkService(IReferralLinkService):
    def __init__(self, vk_bot_link: str, tg_bot_link: str, max_bot_link: str, source: Sources, image_path: str):
        self.vk_bot_link = vk_bot_link
        self.tg_bot_link = tg_bot_link
        self.max_bot_link = max_bot_link
        self.source = source
        self.image_path = image_path

    def generate_post(self, user_id: int) -> Repost:
        vk_url = f"{self.vk_bot_link}?ref={user_id}_{self.source.value}"
        tg_url = f"{self.tg_bot_link}?start={user_id}_{self.source.value}"
        max_url = f"{self.max_bot_link}?start={user_id}_{self.source.value}"

        text = (
            "🦅 Присоединяйся к Большой команде ЛДПР!\n\n"
            "Стань частью движения, которое меняет страну к лучшему.\n"
            "Выполняй задания, проходи обучение, зарабатывай баллы и обменивай их на эксклюзивные подарки в нашем магазине!\n\n"
            "Приглашай друзей и получай дополнительные баллы за каждого:\n"
            f"🔹 ВКонтакте: {vk_url}\n"
            f"🔹 Telegram: {tg_url}\n"
            f"🔹 MAX: {max_url}\n\n"
            "Твоё будущее и будущее страны — в твоих руках!"
        )
        return Repost(text=text, image_path=self.image_path)
