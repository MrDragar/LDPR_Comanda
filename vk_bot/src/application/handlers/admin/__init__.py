from vkbottle.bot import BotLabeler

from .post import router as post_router

full_labeler = BotLabeler()

full_labeler.load(post_router)
