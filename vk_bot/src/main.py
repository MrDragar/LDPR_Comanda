import logging
from aiogram import Bot as TgBot
from aiogram.client.session.aiohttp import AiohttpSession
from vkbottle import Bot, DocMessagesUploader, PhotoMessageUploader
from src.application.handlers import full_labeler as root_labeler
from src.application.middlewares import DIProvideMiddleware
from src.core import config
from src.core.containers import Container



def main():
    logging.basicConfig(
        level=config.log_level,
        format=config.log_format,
        filename=config.log_file,
        filemode="a"
    )

    container = Container()

    bot = Bot(token=config.VK_API_TOKEN)
    tg_bot = TgBot(
        token=config.TG_API_TOKEN,
        session=AiohttpSession(proxy=config.proxy)
    )
    bot.api.admin_ids = config.admin_ids
    bot.api.log_chat = config.log_chat

    DIProvideMiddleware.container = container
    DIProvideMiddleware.tg_bot = tg_bot
    DIProvideMiddleware.state_dispenser = bot.state_dispenser
    DIProvideMiddleware.doc_uploader = DocMessagesUploader(bot.api)
    DIProvideMiddleware.photo_uploader = PhotoMessageUploader(bot.api)
    bot.labeler.message_view.register_middleware(DIProvideMiddleware)
    bot.labeler.raw_event_view.register_middleware(DIProvideMiddleware)

    bot.labeler.load(root_labeler)

    async def init_db():
        await container.database().create_database()

    bot.loop_wrapper.add_task(init_db())

    logging.info("Starting VK bot via LoopWrapper...")
    bot.run_forever()


if __name__ == "__main__":
    main()