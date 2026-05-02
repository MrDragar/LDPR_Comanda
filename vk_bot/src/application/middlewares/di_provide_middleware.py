from vkbottle import BaseMiddleware, DocMessagesUploader
from vkbottle.bot import Message


class DIProvideMiddleware(BaseMiddleware[Message]):
    container = None
    state_dispenser = None
    doc_uploader = None
    photo_uploader = None
    tg_bot = None

    async def pre(self):
        self.send({
            **self.container.providers,
            "state_dispenser": self.state_dispenser,
            "doc_uploader": self.doc_uploader,
            "photo_uploader": self.photo_uploader,
            "tg_bot": self.tg_bot
        })
