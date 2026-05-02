from vkbottle.bot import BotLabeler
from .start import router as start_router, start_command_router
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
from .admin.post import router as admin_router

full_labeler = BotLabeler()

# Порядок важен: сначала проверяем команду старт, потом состояния, потом общий старт (fallback)
full_labeler.load(start_command_router)
full_labeler.load(admin_router)
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
full_labeler.load(start_router)