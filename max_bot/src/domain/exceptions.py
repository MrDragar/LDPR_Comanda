class DomainError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UserNotFoundError(Exception):
    ...


class PhoneBadFormatError(Exception):
    ...


class PhoneAlreadyExistsError(Exception):
    ...


class PhoneBadCountryError(Exception):
    ...


class EmailBadFormatError(Exception):
    ...


class EmailAlreadyExistsError(Exception):
    ...


class FioFormatError(Exception):
    ...


class NotFoundRegionError(Exception):
    ...


class ReferralAlreadyExistsError(Exception):
    pass


class TaskNotCompletedError(DomainError):
    """Вызывается, если действие пользователя в ВК не найдено"""
    pass


class VKApiError(DomainError):
    """Вызывается при ошибках обращения к VK API"""
    pass


class AuthError(Exception):
    pass


class AuthBadUserError(AuthError):
    pass


class PetitionError(Exception):
    pass


class CandidateNotFoundError(Exception):
    pass


class QuestionNotFoundError(Exception):
    pass


class PetitionAlreadyModeratedError(Exception):
    pass


class CandidateAlreadyExistsError(Exception):
    pass


class PetitionAlreadyTakenError(Exception):
    pass


class PetitionNotAvailableError(Exception):
    pass


class CandidateNotAssignedError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class HillError(Exception):
    pass
