import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from src.application.states import LearningStates
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import IUserService, ILearningService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

# Маппинг для проверки ответов
_LETTER_TO_INDEX = {"А": 0, "Б": 1, "В": 2, "Г": 3}
_LETTERS_LIST = ["А", "Б", "В", "Г"]


def _build_quiz_kb() -> types.ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопками А, Б, В, Г"""
    builder = ReplyKeyboardBuilder()
    # Расположим 2x2 для удобства
    builder.button(text="А")
    builder.button(text="Б")
    builder.button(text="В")
    builder.button(text="Г")
    builder.button(text="На главную")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def _format_question_text(q_text: str, options: list[str]) -> str:
    """Форматирует текст вопроса, добавляя варианты ответов прямо в сообщение"""
    options_text = "\n".join([f"{letter}. {opt}" for letter, opt in zip(_LETTERS_LIST, options)])
    return f"{q_text}\n\n{options_text}\n\nВыберите вариант (А, Б, В или Г):"


@router.message(F.text == "Обучение")
@router.message(F.text == "Пройти обучение ещё раз")
async def open_learning(message: types.Message, user_service: IUserService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        return await message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания.",
            reply_markup=get_role_menu_keyboard(u.role)
        )

    builder = ReplyKeyboardBuilder()
    builder.button(text="Начать тест")
    builder.button(text="На главную")
    builder.adjust(1)

    try:
        await message.answer_document(types.FSInputFile('docs/Презентация_обучение агитаторов.pdf'))
        await message.answer(
            "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
            "Для успешного прохождения теста необходимо ответить на 9 вопросов из 10.",
            parse_mode="HTML",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    except Exception as e:
        logger.error(f"Error sending doc: {e}")
        await message.answer("Ошибка при отправке материалов. Попробуйте позже.")


@router.message(F.text == "Начать тест")
async def start_quiz(message: types.Message, learning_service: ILearningService, state: FSMContext):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        full_text = _format_question_text(f"Вопрос 1/10\n{q_text}", options)

        await state.update_data(q_idx=0, score=0)
        await state.set_state(LearningStates.quiz)
        await message.answer(full_text, reply_markup=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await message.answer("Ошибка запуска теста.")


@router.message(LearningStates.quiz)
async def handle_quiz_answer(message: types.Message, learning_service: ILearningService,
                             state: FSMContext, user_service: IUserService):
    # Обработка отмены или выхода
    if message.text == "Отмена" or message.text == "На главную":
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer("Тест прерван.", reply_markup=get_role_menu_keyboard(role))
        return

    data = await state.get_data()
    q_idx = data.get("q_idx", 0)
    score = data.get("score", 0)

    # Приводим ответ к верхнему регистру и убираем пробелы
    user_answer = message.text.strip().upper()

    # Проверяем, что ответ - это одна из допустимых букв
    if user_answer not in _LETTER_TO_INDEX:
        await message.answer("Пожалуйста, выберите один из вариантов: А, Б, В или Г.",
                             reply_markup=_build_quiz_kb())
        return

    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)

        # Получаем индекс ответа пользователя
        user_choice_idx = _LETTER_TO_INDEX[user_answer]

        if user_choice_idx == correct_idx:
            score += 1

        next_q = q_idx + 1
        if next_q >= 10:
            result = await learning_service.finish_quiz(message.from_user.id, Sources.TG, score)
            await state.clear()

            # Обновляем роль пользователя, так как она могла измениться внутри finish_quiz
            role = await user_service.get_user_role(message.from_user.id, Sources.TG)

            builder = ReplyKeyboardBuilder()
            if result["status"] == "fail":
                builder.button(text="На главную")
                builder.button(text="Пройти обучение ещё раз")
            else:
                builder.button(text="На главную")
            builder.adjust(1)

            await message.answer(result["message"],
                                 reply_markup=builder.as_markup(resize_keyboard=True))
        else:
            await state.update_data(q_idx=next_q, score=score)
            q_text_next, options_next, _ = await learning_service.get_question(next_q)
            full_text_next = _format_question_text(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                                   options_next)
            await message.answer(full_text_next, reply_markup=_build_quiz_kb())
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await message.answer("Произошла ошибка. Попробуйте начать заново.")


@router.message(F.text == "На главную")
async def back_to_main(message: types.Message, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
