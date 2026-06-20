from maxapi import Router
from .menu import router as menu_router
from .profile import router as profile_router

router = Router()
router.include_routers(menu_router, profile_router)
