from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.domain.entities.task import OnlineTask, OfflineTask, TaskType


def get_task_type_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Онлайн", payload="task_type_online"),
                CallbackButton(text="Офлайн", payload="task_type_offline"))
    return builder


def get_online_tasks_keyboard(tasks: list[OnlineTask], page: int, total_pages: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.row(CallbackButton(text=f"#{t.id} {t.type.value}", payload=f"view_online_{t.id}"))
    if page > 1:
        builder.row(CallbackButton(text="⬅️ Назад", payload=f"prev_online_{page - 1}"))
    if page < total_pages:
        builder.row(CallbackButton(text="Вперёд ➡️", payload=f"next_online_{page + 1}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="back_to_menu"))
    return builder


def get_offline_tasks_keyboard(tasks: list[OfflineTask], page: int, total_pages: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        title = t.title[:20] + "..." if len(t.title) > 20 else t.title
        builder.row(CallbackButton(text=f"#{t.id} {title}", payload=f"view_offline_{t.id}"))
    if page > 1:
        builder.row(CallbackButton(text="⬅️ Назад", payload=f"prev_offline_{page - 1}"))
    if page < total_pages:
        builder.row(CallbackButton(text="Вперёд ➡️", payload=f"next_offline_{page + 1}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="back_to_menu"))
    return builder


def get_online_task_view_keyboard(task_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Проверить", payload=f"check_online_{task_id}"))
    builder.row(CallbackButton(text="Назад к списку", payload="back_online_list"))
    return builder


def get_offline_task_view_keyboard(task_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Принять", payload=f"accept_offline_{task_id}"))
    builder.row(CallbackButton(text="Назад к списку", payload="back_offline_list"))
    return builder


def get_my_tasks_keyboard(tasks: list) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        status_text = t.status.value
        title = t.task.title[:15] + "..." if len(t.task.title) > 15 else t.task.title
        builder.row(CallbackButton(text=f"#{t.task.id} {title} ({status_text})", payload=f"view_my_task_{t.task.id}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="back_to_menu"))
    return builder


def get_my_task_view_keyboard(task_id: int, is_in_progress: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if is_in_progress:
        builder.row(CallbackButton(text="❌ Отменить задание", payload=f"cancel_my_task_{task_id}"))
    builder.row(CallbackButton(text="🔙 Назад", payload="back_to_my_tasks"))
    return builder


def get_task_type_admin_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for t in TaskType:
        builder.row(CallbackButton(text=t.value, payload=f"set_type_{t.value}"))
    return builder


def get_admin_verify_task_keyboard(task_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Список участников", payload=f"list_users_{task_id}_1"))
    builder.row(CallbackButton(text="Назад к списку задач", payload="back_to_verify"))
    return builder


def get_admin_verify_users_keyboard(task_id: int, uid: int, source: str, page: int, total_pages: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.row(CallbackButton(text="⬅️ Назад", payload=f"list_users_{task_id}_{page - 1}"))
    if page < total_pages:
        builder.row(CallbackButton(text="Вперёд ➡️", payload=f"list_users_{task_id}_{page + 1}"))
    builder.row(CallbackButton(text="✅ Принять", payload=f"verify_action_{task_id}_{uid}_{source}_accept"))
    builder.row(CallbackButton(text="❌ Отклонить", payload=f"verify_action_{task_id}_{uid}_{source}_decline"))
    builder.row(CallbackButton(text="К задаче", payload=f"view_task_{task_id}"))
    return builder
