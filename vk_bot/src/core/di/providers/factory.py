from typing import Callable, Any

from .provider import Provider, T


class Factory(Provider[T]):
    __args: tuple[Any, ...]
    __kwargs:  dict[str, Any]
    _provides: Callable[..., T]

    def __init__(self, provides: Callable[..., T], *args, **kwargs):
        super().__init__(provides)
        self.__args = args
        self.__kwargs = kwargs

    def __call__(self) -> T:
        return self._provides(
            *self._provide_args(*self.__args),
            **self._provide_kwargs(**self.__kwargs)
        )

