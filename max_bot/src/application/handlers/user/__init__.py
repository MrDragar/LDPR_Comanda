from maxapi import Router
from .menu import router as menu_router
from .lottery import router as lottery_router
from .profile import router as profile_router
from .tasks import router as tasks_router
from .learning import router as learning_router
from .shop import router as shop_router
from .closed_events import router as closed_events_router


router = Router()
router.include_routers(
    tasks_router,
    learning_router,
    shop_router,
    closed_events_router,
    menu_router,
    lottery_router,
    profile_router
)
