from .provider import Provider, T


class Object(Provider[T]):
    _provides: T

    def __init__(self, provides: T):
        super().__init__(provides)

    def __call__(self) -> T:
        return self._provides
