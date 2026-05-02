from typing import Callable

from .provider import Provider, T


class Singleton(Provider[T]):
    _provides: T

    def __init__(self, provides: Callable[..., T], *args, **kwargs):
        super().__init__(
            provides(
                *self._provide_args(*args), **self._provide_kwargs(**kwargs)
            )
        )

    def __call__(self) -> T:
        return self._provides
