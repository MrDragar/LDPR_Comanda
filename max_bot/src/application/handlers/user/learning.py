import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.states import LearningStates
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import IUserService, ILearningService
from src.application.keyboards.learning_keyboard import get_quiz_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message_created(F.message.body.text == "Обучение")
async def open_learning(event: MessageCreated, user_service: IUserService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        return await event.message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания.",
            attachments=[get_role_menu_keyboard(u.role).as_markup()]
        )

    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Начать тест"))
    builder.row(MessageButton(text="На главную"))

    await event.message.answer(
        "'Презентация'\n"
        "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
        "Для успешного прохождения теста необходимо ответить на 7 вопросов из 10.",
        attachments=[builder.as_markup()]
    )


@router.message_created(F.message.body.text == "Начать тест")
async def start_quiz(event: MessageCreated, learning_service: ILearningService,
                     context: MemoryContext):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await context.update_data(q_idx=0, score=0)
        await context.set_state(LearningStates.QUIZ)
        await event.message.answer(f"Вопрос 1/10\n{q_text}",
                                   attachments=[get_quiz_keyboard(options).as_markup()])
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await event.message.answer("Ошибка запуска теста.")


@router.message_created(LearningStates.QUIZ)
async def handle_quiz_answer(event: MessageCreated, learning_service: ILearningService,
                             context: MemoryContext, user_service: IUserService):
    if event.message.body.text == "Отмена":
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Тест прерван.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    data = await context.get_data()
    q_idx = data.get("q_idx", 0)
    score = data.get("score", 0)
    user_answer = event.message.body.text.strip()

    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)
        if user_answer == options[correct_idx]:
            score += 1

        next_q = q_idx + 1
        if next_q >= 10:
            result = await learning_service.finish_quiz(event.from_user.user_id, Sources.MAX, score)
            await context.clear()

            builder = InlineKeyboardBuilder()
            if result["status"] == "fail":
                builder.row(MessageButton(text="На главную"))
                builder.row(MessageButton(text="Пройти обучение ещё раз"))
            else:
                builder.row(MessageButton(text="На главную"))

            await event.message.answer(result["message"], attachments=[builder.as_markup()])
        else:
            await context.update_data(q_idx=next_q, score=score)
            q_text_next, options_next, _ = await learning_service.get_question(next_q)
            await event.message.answer(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                       attachments=[get_quiz_keyboard(options_next).as_markup()])
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await event.message.answer("Произошла ошибка. Попробуйте начать заново.")


@router.message_created(F.message.body.text == "Пройти обучение ещё раз")
async def retry_quiz(event: MessageCreated, learning_service: ILearningService,
                     context: MemoryContext):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await context.update_data(q_idx=0, score=0)
        await context.set_state(LearningStates.QUIZ)
        await event.message.answer(f"Вопрос 1/10\n{q_text}",
                                   attachments=[get_quiz_keyboard(options).as_markup()])
    except Exception as e:
        logger.error(f"Retry quiz error: {e}")
        await event.message.answer("Ошибка перезапуска теста.")
