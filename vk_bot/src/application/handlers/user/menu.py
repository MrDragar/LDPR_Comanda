import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text
from src.application.states import UserTaskStates
from src.domain.entities import Sources

logger = logging.getLogger(__name__)
router = BotLabeler()


def get_main_menu_kb():
    return Keyboard(one_time=False).add(Text("Выполнить задание")).row().add(Text("Мои задания")).row().add(Text("Личный кабинет")).get_json()


@router.message(text=["Меню", "На главную"])
async def show_menu(message: Message):
    await message.answer("Главное меню:", keyboard=get_main_menu_kb())


@router.message(text=["Выполнить задание"])
async def select_task_type(message: Message, state_dispenser):
    kb = Keyboard(inline=True).add(Text("Онлайн")).add(Text("Офлайн"))
    await state_dispenser.set(message.from_id, UserTaskStates.SELECT_TYPE)
    await message.answer("Выберите тип задания:", keyboard=kb.get_json())


@router.message(text=["Мои задания"])
async def my_tasks(message: Message, offline_task_service, user_service, state_dispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        return await message.answer("У вас нет активных заданий.")
    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Text(f"#{t.task.id} {t.task.title} ({t.status.value})"))
        kb.row()
    await state_dispenser.set(message.from_id, UserTaskStates.MY_TASKS)
    await message.answer("Ваши задания:", keyboard=kb.get_json())
