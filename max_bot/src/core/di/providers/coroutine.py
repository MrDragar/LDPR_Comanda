from typing import Callable, Any, Awaitable

from .provider import Provider, T


class Coroutine(Provider[T]):
    __kwargs: dict[str, Any]
    _provides: Callable[..., Awaitable[T]]

    def __init__(self, provides: Callable[..., Awaitable[T]], **kwargs):
        super().__init__(provides)
        self.__kwargs = kwargs

    def __call__(self, *args, **kwargs) -> Awaitable[T]:
        return self._provides(*args, **kwargs, **self._provide_kwargs(**self.__kwargs))