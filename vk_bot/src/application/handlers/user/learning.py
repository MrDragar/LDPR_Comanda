import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import LearningStates
from src.application.utils import handle_cancel
from src.domain.entities.user import Sources, UserGrade
from src.services.interfaces import IUserService, ILearningService, INotificationService

logger = logging.getLogger(__name__)
router = BotLabeler()


def _build_quiz_kb(options: list[str]) -> str:
    kb = Keyboard(one_time=True, inline=False)
    for opt in options:
        kb.add(Text(opt))
    return kb.get_json()


@router.message(text=["Обучение"])
async def open_learning(message: Message, user_service: IUserService) -> None:
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.grade not in (UserGrade.BIG_TEAM_MEMBER, UserGrade.AGITATOR, UserGrade.RESERVE):
        await message.answer(
            "Для разблокировки этого раздела необходим ранг \"Участник большой команды\". "
            "Для его достижения выполните 3 онлайн задания."
        )
        kb = Keyboard(one_time=True, inline=False).add(Text("На главную"))
        return await message.answer("Меню", keyboard=kb.get_json())

    await message.answer(
        "<Презентация>\n"
        "Внимательно изучите презентацию. Когда будете готовы, нажмите \"Начать тест\". "
        "Для успешного прохождения теста необходимо ответить на 7 вопросов из 10."
    )
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("Начать тест")).row().add(Text("На главную"))
    await message.answer("Действия:", keyboard=kb.get_json())


@router.message(text=["Начать тест"])
async def start_quiz(message: Message, learning_service: ILearningService,
                     state_dispenser: BuiltinStateDispenser) -> None:
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await state_dispenser.set(message.from_id, LearningStates.QUIZ, q_idx=0, score=0)
        await message.answer(f"Вопрос 1/10\n{q_text}", keyboard=_build_quiz_kb(options))
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
    user_answer = message.text.strip()
    try:
        q_text, options, correct_idx = await learning_service.get_question(q_idx)
        if user_answer == options[correct_idx]:
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
            await message.answer(f"Вопрос {next_q + 1}/10\n{q_text_next}",
                                 keyboard=_build_quiz_kb(options_next))
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await message.answer("Произошла ошибка. Попробуйте начать заново.")


@router.message(text=["Пройти обучение ещё раз"])
async def retry_quiz(message: Message, learning_service: ILearningService,
                     state_dispenser: BuiltinStateDispenser) -> None:
    try:
        q_text, options, _ = await learning_service.get_question(0)
        await state_dispenser.set(message.from_id, LearningStates.QUIZ, q_idx=0, score=0)
        await message.answer(f"Вопрос 1/10\n{q_text}", keyboard=_build_quiz_kb(options))
    except Exception as e:
        logger.error(f"Retry quiz error: {e}")
        await message.answer("Ошибка перезапуска теста.")
