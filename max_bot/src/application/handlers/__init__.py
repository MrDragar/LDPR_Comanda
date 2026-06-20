from maxapi import Router
from .start import router as start_router, catch_all_router
from .personal_data import router as pd_router
from .get_fio import router as fio_router
from .get_birthday import router as birthday_router
from .get_phone import router as phone_router
from .get_region import router as region_router
from .get_news_subscription import router as news_router
from .auth_confirmation import router as auth_router
from .admin_tools import router as admin_tools_router
from .headliners import router as headliners_router
from .user import router as user_router

full_router = Router()
full_router.include_routers(
    start_router, pd_router, fio_router, birthday_router,
    phone_router, region_router, news_router, auth_router, admin_tools_router, headliners_router, user_router
)

full_router.include_routers(catch_all_router)
