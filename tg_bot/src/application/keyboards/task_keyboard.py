from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.domain.entities.task import OnlineTask, OfflineTask, TaskType


def get_task_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Онлайн", callback_data="task_type_online")
    builder.button(text="Офлайн", callback_data="task_type_offline")
    builder.adjust(2)
    return builder.as_markup()


def get_online_tasks_keyboard(tasks: list[OnlineTask], page: int,
                              total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=f"#{t.id} {t.type.value}", callback_data=f"view_online_{t.id}")

    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"prev_online_{page - 1}")
    if page < total_pages:
        builder.button(text="Вперёд ➡️", callback_data=f"next_online_{page + 1}")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_offline_tasks_keyboard(tasks: list[OfflineTask], page: int,
                               total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        title = t.title[:20] + "..." if len(t.title) > 20 else t.title
        builder.button(text=f"#{t.id} {title}", callback_data=f"view_offline_{t.id}")

    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"prev_offline_{page - 1}")
    if page < total_pages:
        builder.button(text="Вперёд ➡️", callback_data=f"next_offline_{page + 1}")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_online_task_view_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Проверить", callback_data=f"check_online_{task_id}")
    builder.button(text="Назад к списку", callback_data="back_online_list")
    builder.adjust(1)
    return builder.as_markup()


def get_offline_task_view_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Принять", callback_data=f"accept_offline_{task_id}")
    builder.button(text="Назад к списку", callback_data="back_offline_list")
    builder.adjust(1)
    return builder.as_markup()


def get_my_tasks_keyboard(tasks: list, page: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        status_text = t.status.value
        title = t.task.title[:15] + "..." if len(t.task.title) > 15 else t.task.title
        builder.button(text=f"#{t.task.id} {title} ({status_text})",
                       callback_data=f"view_my_task_{t.task.id}")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_my_task_view_keyboard(task_id: int, is_in_progress: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_in_progress:
        builder.button(text="❌ Отменить задание", callback_data=f"cancel_my_task_{task_id}")
    builder.button(text="🔙 Назад", callback_data="back_to_my_tasks")
    builder.adjust(1)
    return builder.as_markup()


def get_task_type_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in TaskType:
        builder.button(text=t.value, callback_data=f"set_type_{t.value}")
    builder.adjust(1)
    return builder.as_markup()
