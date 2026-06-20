import logging

from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import MessageButton, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import LearningStates
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import ILearningService, IUserService

logger = logging.getLogger(__name__)
router = Router()


def _text_keyboard(buttons: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for button in buttons:
        builder.row(MessageButton(text=button))
    return builder


@router.message_created(F.message.body.text == "Обучение")
async def open_learning(event: MessageCreated, user_service: IUserService):
    user = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if user.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        await event.message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания.",
            attachments=[get_role_menu_keyboard(user.role).as_markup()]
        )
        return

    await event.message.answer(
        "'Презентация'\n"
        "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
        "Для успешного прохождения теста необходимо ответить на 7 вопросов из 10.",
        attachments=[_text_keyboard(["Начать тест", "На главную"]).as_markup()]
    )


@router.message_created(F.message.body.text.in_(["Начать тест", "Пройти обучение ещё раз"]))
async def start_quiz(event: MessageCreated, learning_service: ILearningService,
                     context: MemoryContext):
    try:
        question, options, _ = await learning_service.get_question(0)
        await context.update_data(q_idx=0, score=0)
        await context.set_state(LearningStates.QUIZ)
        await event.message.answer(
            f"Вопрос 1/10\n{question}",
            attachments=[_text_keyboard(options).as_markup()]
        )
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await event.message.answer("Ошибка запуска теста.")


@router.message_created(LearningStates.QUIZ)
async def handle_quiz_answer(event: MessageCreated, learning_service: ILearningService,
                             context: MemoryContext, user_service: IUserService):
    answer = (event.message.body.text or "").strip()
    if answer in ("Отмена", "На главную"):
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Тест прерван.", attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    data = await context.get_data()
    q_idx = data.get("q_idx", 0)
    score = data.get("score", 0)

    try:
        _, options, correct_idx = await learning_service.get_question(q_idx)
        if answer == options[correct_idx]:
            score += 1

        next_q = q_idx + 1
        if next_q >= 10:
            result = await learning_service.finish_quiz(event.from_user.user_id, Sources.MAX, score)
            await context.clear()
            buttons = ["На главную"]
            if result["status"] == "fail":
                buttons.append("Пройти обучение ещё раз")
            await event.message.answer(result["message"], attachments=[_text_keyboard(buttons).as_markup()])
            return

        await context.update_data(q_idx=next_q, score=score)
        question, next_options, _ = await learning_service.get_question(next_q)
        await event.message.answer(
            f"Вопрос {next_q + 1}/10\n{question}",
            attachments=[_text_keyboard(next_options).as_markup()]
        )
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await event.message.answer("Произошла ошибка. Попробуйте начать заново.")
