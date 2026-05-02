from aiogram.dispatcher.router import Router

from .admin import router as admin_router
from .personal_data import router as pd_router
from .get_membership import router as membership_router
from .get_fio import router as fio_router
from .get_gender import router as gender_router
from .get_phone import router as phone_router
from .get_birth_date import router as birth_data_router
from .get_region import router as region_router
from .get_email import router as email_router
from .get_city import router as city_router
from .get_wish_to_join import router as wish_to_join_router
from .get_home_address import router as home_address_router
from .get_news_subscription import router as news_subscription_router
from .start import router as start_router, start_command_router

router = Router(name=__name__)

router.include_router(start_command_router)
router.include_router(admin_router)
router.include_router(pd_router)
router.include_router(membership_router)
router.include_router(fio_router)
router.include_router(region_router)
router.include_router(birth_data_router)
router.include_router(phone_router)
router.include_router(email_router)
router.include_router(gender_router)
router.include_router(city_router)
router.include_router(wish_to_join_router)
router.include_router(home_address_router)
router.include_router(news_subscription_router)
router.include_router(start_router)
