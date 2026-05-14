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
