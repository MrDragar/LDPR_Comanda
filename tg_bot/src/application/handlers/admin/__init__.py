from aiogram import Router

from src.application.filters import AdminFilter
from .post import router as post_router

router = Router()
router.message.filter(AdminFilter())
router.include_router(post_router)
