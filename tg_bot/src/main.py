import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from src.application.handlers import router as root_router
from src.application.middlewares import DIProvideMiddleware
from src.core import config
from src.core.containers import Container


async def main():
    logging.basicConfig(
        level=config.log_level,
        format=config.log_format,
        filename=config.log_file,
        filemode="a"
    )
    bot = Bot(
        token=config.TG_API_TOKEN,
        session=AiohttpSession(proxy=config.proxy)
    )
    container = Container()
    logging.debug(f"{vars(container)}, {container.user_service}")
    logging.debug("")
    await container.database().create_database()
    di_middleware = DIProvideMiddleware(container)
    dp = Dispatcher()
    dp.update.middleware(di_middleware)
    dp.include_router(root_router)
    logging.debug("Starting bot")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
