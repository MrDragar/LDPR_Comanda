from maxapi import Router
from .start import router as start_router, catch_all_router
from .personal_data import router as pd_router
from .get_membership import router as membership_router
from .get_fio import router as fio_router
from .get_gender import router as gender_router
from .get_birthday import router as birthday_router
from .get_phone import router as phone_router
from .get_email import router as email_router
from .get_region import router as region_router
from .get_city import router as city_router
from .get_wish_to_join import router as wish_to_join_router
from .get_home_address import router as home_address_router
from .get_news_subscription import router as news_router
from .user import router as user_router

full_router = Router()
full_router.include_routers(
    start_router, pd_router, membership_router, fio_router, gender_router,
    birthday_router, phone_router, email_router, region_router, city_router,
    wish_to_join_router, home_address_router, news_router, user_router
)
full_router.include_routers(catch_all_router)