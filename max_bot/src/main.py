import asyncio
import logging

from src.core import config
from src.core.containers import Container
from src.application.middlewares.di_provide_middleware import DIProvideMiddleware
from src.application.handlers import full_router


def main():
    logging.basicConfig(
        level=config.log_level,
        format=config.log_format,
        filename=config.log_file,
        filemode="a"
    )

    container = Container()
    DIProvideMiddleware.container = container

    bot = container.bot()
    dp = container.dp()

    dp.inner_middlewares.append(DIProvideMiddleware())
    dp.include_routers(full_router)

    async def on_startup():
        await container.database().create_database()
        logging.info("Database initialized.")

    if hasattr(dp, 'on_started_func'):
        dp.on_started_func = on_startup
    elif hasattr(dp, 'startup'):
        dp.startup.register(on_startup)

    logging.info("Starting Max bot via Polling...")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()