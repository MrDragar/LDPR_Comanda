from vkbottle.bot import BotLabeler
from .start import router as start_router, start_command_router
from .admin.ca import router as ca_router
from .admin.tasks import router as admin_tasks_router
from .user.menu import router as user_menu_router
from .user.tasks import router as user_tasks_router
from .user.profile import router as user_profile_router
from .user.learning import router as user_learning_router
from .personal_data import router as pd_router
from .get_membership import router as membership_router
from .get_fio import router as fio_router
from .get_gender import router as gender_router
from .get_birth_date import router as birth_router
from .get_phone import router as phone_router
from .get_email import router as email_router
from .get_region import router as region_router
from .get_city import router as city_router
from .get_wish_to_join import router as wish_router
from .get_home_address import router as home_router
from .get_news_subscription import router as news_router
from .check_subscription import router as check_router
from .admin.post import router as admin_router

full_labeler = BotLabeler()

full_labeler.load(start_command_router)
full_labeler.load(admin_router)
full_labeler.load(ca_router)
full_labeler.load(admin_tasks_router)
full_labeler.load(user_menu_router)
full_labeler.load(user_tasks_router)
full_labeler.load(user_profile_router)
full_labeler.load(user_learning_router)
full_labeler.load(pd_router)
full_labeler.load(pd_router)
full_labeler.load(membership_router)
full_labeler.load(fio_router)
full_labeler.load(gender_router)
full_labeler.load(birth_router)
full_labeler.load(phone_router)
full_labeler.load(email_router)
full_labeler.load(region_router)
full_labeler.load(city_router)
full_labeler.load(wish_router)
full_labeler.load(home_router)
full_labeler.load(news_router)
full_labeler.load(check_router)
full_labeler.load(start_router)
