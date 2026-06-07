from maxapi import Router
from .menu import router as menu_router
from .lottery import router as lottery_router
from .profile import router as profile_router


router = Router()
router.include_routers(menu_router, lottery_router, profile_router)
