import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text, PhotoMessageUploader, Bot, DocMessagesUploader
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import LearningStates
from src.application.utils import handle_cancel
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import IUserService, ILearningService, INotificationService

logger = logging.getLogger(__name__)
router = BotLabeler()

# Маппинг индексов в русские буквы для кнопок и парсинга ответа
_INDEX_TO_LETTER = {0: "А", 1: "Б", 2: "В", 3: "Г"}
_LETTER_TO_INDEX = {"А": 0, "Б": 1, "В": 2, "Г": 3}


def _build_quiz_kb() -> str:
    """Создает клавиатуру с кнопками А, Б, В, Г"""
    kb = Keyboard(one_time=True, inline=False)
    # Расположим кнопки в два ряда по две для удобства нажатия
    kb.add(Text("А")).add(Text("Б")).row()
    kb.add(Text("В")).add(Text("Г")).row()
    kb.add(Text("На главную"))
    return kb.get_json()


def _format_question_text(q_text: str, options: list[str]) -> str:
    """Форматирует текст вопроса, добавляя варианты ответов прямо в сообщение"""
    # Используем буквы А, Б, В, Г из словаря
    letters = ["А", "Б", "В", "Г"]
    options_text = "\n".join([f"{letter}. {opt}" for letter, opt in zip(letters, options)])
    return f"{q_text}\n\n{options_text}\n\nВыберите вариант (А, Б, В или Г):"


@router.message(text=["Обучение"])
@router.message(text=["Пройти обучение ещё раз"])
async def open_learning(message: Message, user_service: IUserService,
                        doc_uploader: DocMessagesUploader) -> None:
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        await message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания."
        )
        kb = Keyboard(one_time=True, inline=False).add(Text("На главную"))
        return await message.answer("Меню", keyboard=kb.get_json())
    try:
        doc = await doc_uploader.upload('docs/Презентация_обучение агитаторов.pdf',
                                        peer_id=message.peer_id)
        await message.answer(
            "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
            "Для успешного прохождения теста необходимо ответить на 9 вопросов из 10.",
            attachment=doc
        )
    except Exception as e:
        logger.error(e)
        return await message.answer("Возникла ошибка при отправке обучающих материалов")

    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("Начать тест")).row().add(Text("На главную"))
    await message.answer("Действия:", keyboard=kb.get_json())


@router.message(text=["Начать тест"])
async def start_quiz(message: Message, learning_service: ILearningService,
                     user_service: IUserService,
                     state_dispenser: BuiltinStateDispenser) -> None:
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        await message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания."
        )
        kb = Keyboard(one_time=True, inline=False).add(Text("На главную"))
        return await message.answer("Меню", keyboard=kb.get_json())
    try:
        q_text, options, _ = await learning_service.get_question(0)
        full_text = _format_question_text(f"Вопрос 1/10\n{q_text}", options)

        await state_dispenser.set(message.from_id, LearningStates.QUIZ, q_idx=0, score=0)
        await message.answer(full_text, keyboard=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await message.answer("Ошибка запуска теста.")


@router.message(state=LearningStates.QUIZ)
async def handle_quiz_answer(message: Message, learning_service: ILearningService,
                             state_dispenser: BuiltinStateDispenser,
                             user_service: IUserService) -> None:
    if await handle_cancel(message, state_dispenser, user_service): return

    state = await state_dispenser.get(message.from_id)
    if not state: return

    q_idx = state.payload.get("q_idx", 0)
    score = state.payload.get("score", 0)

    # Приводим ответ к верхнему регистру и убираем пробелы
    user_answer = message.text.strip().upper()

    # Проверяем, что ответ - это одна из допустимых русских букв
    if user_answer not in _LETTER_TO_INDEX:
        await message.answer("Пожалуйста, выберите один из вариантов: А, Б, В или Г.",
                             keyboard=_build_quiz_kb())
        return

    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)

        # Получаем индекс ответа пользователя
        user_choice_idx = _LETTER_TO_INDEX[user_answer]

        if user_choice_idx == correct_idx:
            score += 1

        next_q = q_idx + 1
        if next_q >= 10:
            result = await learning_service.finish_quiz(message.from_id, Sources.VK, score)
            await state_dispenser.delete(message.from_id)
            kb = Keyboard(one_time=False, inline=False)
            if result["status"] == "fail":
                kb.add(Text("На главную")).row().add(Text("Пройти обучение ещё раз"))
            else:
                kb.add(Text("На главную"))
            await message.answer(result["message"], keyboard=kb.get_json())
        else:
            await state_dispenser.set(message.from_id, LearningStates.QUIZ, q_idx=next_q,
                                      score=score)
            q_text_next, options_next, _ = await learning_service.get_question(next_q)
            full_text_next = _format_question_text(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                                   options_next)
            await message.answer(full_text_next, keyboard=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await message.answer("Произошла ошибка. Попробуйте начать заново.")
