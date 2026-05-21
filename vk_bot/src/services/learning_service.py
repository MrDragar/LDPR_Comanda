import logging
from datetime import datetime
from src.domain.entities.user import Sources, UserGrade
from src.domain.entities.learning import LearningTestAttempt
from src.domain.interfaces import IUnitOfWork, ILearningRepository
from src.services.interfaces import ILearningService, IUserService, IBalanceService
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

# Заглушка: 10 вопросов, правильный ответ всегда 1-й (индекс 0)
_QUESTIONS_STUB = [
    (f"Вопрос {i+1}: Выберите правильный вариант (заглушка)", ["Вариант 1 (Верный)", f"Вариант 2", f"Вариант 3", f"Вариант 4"])
    for i in range(10)
]


class LearningService(ILearningService):
    def __init__(self, uow: IUnitOfWork, repo: ILearningRepository, user_svc: IUserService, balance_svc: IBalanceService):
        self.__uow = uow
        self.__repo = repo
        self.__user_svc = user_svc
        self.__balance_svc = balance_svc

    async def get_question(self, question_index: int) -> tuple[str, list[str], int]:
        if not 0 <= question_index < len(_QUESTIONS_STUB):
            raise DomainError("Вопрос не найден")
        q_text, options = _QUESTIONS_STUB[question_index]
        return q_text, options, 0  # correct_idx всегда 0

    async def finish_quiz(self, user_id: int, user_source: Sources, score: int) -> dict:
        async with self.__uow.atomic():
            prev = await self.__repo.get_attempt(user_id, user_source)
            is_first_pass = not prev or not prev.is_passed

            now = datetime.now()
            attempt = LearningTestAttempt(
                user_id=user_id, user_source=user_source,
                score=score, passed_at=now, is_passed=score >= 7
            )
            await self.__repo.save_attempt(attempt)

            user = await self.__user_svc.get_user(user_id, user_source)
            grade_updated = False
            new_grade = user.grade

            # Апгрейд до Агитатора при первом успешном прохождении
            if score >= 7 and user.grade == UserGrade.BIG_TEAM_MEMBER:
                new_grade = UserGrade.AGITATOR
                grade_updated = True

            if grade_updated:
                await self.__user_svc.update_user_grade(user_id, user_source, new_grade)

            if score >= 7:
                if not is_first_pass:
                    return {
                        "status": "success_repeat",
                        "message": "Поздравляю, вы успешно прошли тест. Поскольу вы его уже проходили, вы не получаете за него баллы"
                    }
                else:
                    await self.__balance_svc.add_balance(user_id, user_source, 50, "Прохождение обучения")
                    msg = "Поздравляем, вы успешно прошли тест. Вам начислено 50 баллов\n"
                    if grade_updated:
                        msg += "Вы получили новый ранг \"Агитатор\". Теперь вам открываются офлайн задания"
                    return {"status": "success_first", "message": msg, "grade": new_grade}
            else:
                return {
                    "status": "fail",
                    "message": "К сожалению, вы не прошли этот тест. Но вы всегда можете пройти его ещё раз"
                }
