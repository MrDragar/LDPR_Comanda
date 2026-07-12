import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageButton, InputMedia
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.states import LearningStates
from src.domain.entities.user import Sources
from src.services.interfaces import IUserService, ILearningService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Маппинг для проверки ответов
_LETTER_TO_INDEX = {"А": 0, "Б": 1, "В": 2, "Г": 3}
_LETTERS_LIST = ["А", "Б", "В", "Г"]


def _build_quiz_kb() -> list:
    """Создает инлайн-клавиатуру с кнопками А, Б, В, Г"""
    builder = InlineKeyboardBuilder()
    # Первый ряд: А, Б
    builder.row(
        MessageButton(text="А"),
        MessageButton(text="Б")
    )
    # Второй ряд: В, Г
    builder.row(
        MessageButton(text="В"),
        MessageButton(text="Г")
    )
    builder.row(
        MessageButton(text="На главную")
    )
    return [builder.as_markup()]


def _format_question_text(q_text: str, options: list[str]) -> str:
    """Форматирует текст вопроса, добавляя варианты ответов прямо в сообщение"""
    options_text = "\n".join([f"{letter}. {opt}" for letter, opt in zip(_LETTERS_LIST, options)])
    return f"{q_text}\n\n{options_text}\n\nВыберите вариант:"


@router.message_created(F.message.body.text == "Обучение")
@router.message_created(F.message.body.text == "Пройти обучение ещё раз")
async def open_learning(event: MessageCreated, user_service: IUserService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)

    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Начать тест"))
    builder.row(MessageButton(text="На главную"))

    try:
        media = InputMedia("docs/Презентация_обучение агитаторов.pdf")
        attachment = await event.bot.upload_media(media)
        await event.send(attachments=[attachment])
    except Exception as e:
        logger.error(f"Media upload error: {e}")
        return await event.message.answer("Возникла ошибка при отправке обучающих материалов")

    await event.message.answer(
        "'Презентация'\n"
        "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
        "Для успешного прохождения теста необходимо ответить на 9 вопросов из 10.",
        attachments=[builder.as_markup()]
    )


@router.message_created(F.message.body.text == "Начать тест")
async def start_quiz(event: MessageCreated, learning_service: ILearningService,
                     context: MemoryContext, user_service: IUserService):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        full_text = _format_question_text(f"Вопрос 1/10\n{q_text}", options)

        await context.update_data(q_idx=0, score=0)
        await context.set_state(LearningStates.QUIZ)
        await event.message.answer(full_text, attachments=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await event.message.answer("Ошибка запуска теста.")


@router.message_created(LearningStates.QUIZ)
async def handle_quiz_answer(event: MessageCreated, learning_service: ILearningService,
                             context: MemoryContext, user_service: IUserService):
    text = event.message.body.text.strip().upper()

    # Обработка отмены или выхода
    if text == "ОТМЕНА" or text == "НА ГЛАВНУЮ":
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Тест прерван.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    # Проверка на валидность ответа (А, Б, В, Г)
    if text not in _LETTER_TO_INDEX:
        await event.message.answer("Пожалуйста, выберите один из вариантов: А, Б, В или Г.",
                                   attachments=_build_quiz_kb())
        return

    data = await context.get_data()
    q_idx = data.get("q_idx", 0)
    score = data.get("score", 0)

    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)

        # Получаем индекс ответа пользователя
        user_choice_idx = _LETTER_TO_INDEX[text]

        if user_choice_idx == correct_idx:
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
            full_text_next = _format_question_text(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                                   options_next)
            await event.message.answer(full_text_next, attachments=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await event.message.answer("Произошла ошибка. Попробуйте начать заново.")
