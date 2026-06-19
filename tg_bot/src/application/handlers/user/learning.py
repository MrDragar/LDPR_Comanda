import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from src.application.states import LearningStates
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import IUserService, ILearningService
from src.application.keyboards.learning_keyboard import get_quiz_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(F.text == "Обучение")
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

    await message.answer(
        "'Презентация'\n"
        "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
        "Для успешного прохождения теста необходимо ответить на 7 вопросов из 10.",
        parse_mode="HTML",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


@router.message(F.text == "Начать тест")
async def start_quiz(message: types.Message, learning_service: ILearningService, state: FSMContext):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await state.update_data(q_idx=0, score=0)
        await state.set_state(LearningStates.quiz)
        await message.answer(f"Вопрос 1/10\n{q_text}", reply_markup=get_quiz_keyboard(options))
    except Exception as e:
        logger.error(f"Start quiz error: {e}")
        await message.answer("Ошибка запуска теста.")


@router.message(LearningStates.quiz)
async def handle_quiz_answer(message: types.Message, learning_service: ILearningService,
                             state: FSMContext, user_service: IUserService):
    if message.text == "Отмена":
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer("Тест прерван.", reply_markup=get_role_menu_keyboard(role))
        return
    data = await state.get_data()
    q_idx = data.get("q_idx", 0)
    score = data.get("score", 0)
    user_answer = message.text.strip()

    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)

        if user_answer == options[correct_idx]:
            score += 1

        next_q = q_idx + 1
        if next_q >= 10:
            result = await learning_service.finish_quiz(message.from_user.id, Sources.TG, score)
            await state.clear()

            role = await user_service.get_user_role(message.from_user.id, Sources.TG)
            builder = ReplyKeyboardBuilder()
            if result["status"] == "fail":
                builder.button(text="На главную")
                builder.button(text="Пройти обучение ещё раз")
            else:
                builder.button(text="На главную")
            builder.adjust(1)

            # Если тест пройден, роль могла измениться (если был апгрейд), поэтому обновляем меню
            if result["status"] in ("success_first", "success_repeat"):
                role = await user_service.get_user_role(message.from_user.id, Sources.TG)

            await message.answer(result["message"],
                                 reply_markup=builder.as_markup(resize_keyboard=True))
        else:
            await state.update_data(q_idx=next_q, score=score)
            q_text_next, options_next, _ = await learning_service.get_question(next_q)
            await message.answer(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                 reply_markup=get_quiz_keyboard(options_next))
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await message.answer("Произошла ошибка. Попробуйте начать заново.")


@router.message(F.text == "Пройти обучение ещё раз")
async def retry_quiz(message: types.Message, learning_service: ILearningService, state: FSMContext):
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await state.update_data(q_idx=0, score=0)
        await state.set_state(LearningStates.quiz)
        await message.answer(f"Вопрос 1/10\n{q_text}", reply_markup=get_quiz_keyboard(options))
    except Exception as e:
        logger.error(f"Retry quiz error: {e}")
        await message.answer("Ошибка перезапуска теста.")


@router.message(F.text == "На главную")
async def back_to_main(message: types.Message, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
