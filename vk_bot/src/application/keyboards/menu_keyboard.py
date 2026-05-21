from vkbottle import Keyboard, Text
from src.domain.entities.user import UserRole


def get_role_menu_keyboard(role: UserRole | None) -> str:
    """Генерирует главное меню в зависимости от роли пользователя."""
    kb = Keyboard(one_time=False)
    kb.add(Text("Выполнить задание")).row()
    kb.add(Text("Мои задания")).row()
    kb.add(Text("Личный кабинет")).row()

    if role in (UserRole.STAFF_RO,
                UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        kb.add(Text("Проверить офлайн задачи")).row()

    if role in (UserRole.COORDINATOR_RO, UserRole.STAFF_CA):
        kb.add(Text("Создать офлайн задачу")).row()
        kb.add(Text("Управление пользователями")).row()

    if role == UserRole.STAFF_CA:
        kb.add(Text("Создать онлайн задачу")).row()

    return kb.get_json()