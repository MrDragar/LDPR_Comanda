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

# User handlers
from .user.profile import router as profile_router
from .user.tasks import router as user_tasks_router
from .user.learning import router as learning_router
from .user.closed_events import router as user_closed_events_router
from .user.shop import router as user_shop_router
from .user.headliners import router as headliners_router

# Admin handlers
from .admin.tasks import router as admin_tasks_router
from .admin.ca import router as admin_ca_router
from .admin.closed_events import router as admin_closed_events_router
from .admin.orders import router as admin_orders_router
from .admin.post import router as admin_post_router
from .admin.shop import router as admin_shop_router

full_router = Router()

full_router.include_routers(
    start_router, pd_router, membership_router, fio_router, gender_router,
    birthday_router, phone_router, email_router, region_router, city_router,
    wish_to_join_router, home_address_router, news_router,
    profile_router, user_tasks_router, learning_router,
    user_closed_events_router, user_shop_router, headliners_router,
    admin_tasks_router, admin_ca_router, admin_closed_events_router,
    admin_orders_router, admin_shop_router, admin_post_router
)

full_router.include_routers(catch_all_router)
