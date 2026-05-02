from typing import Callable as _Callable, Any

from .provider import Provider, T


class Callable(Provider[T]):
    __kwargs:  dict[str, Any]
    _provides: _Callable[..., T]

    def __init__(self, provides: _Callable[..., T], **kwargs):
        super().__init__(provides)
        self.__kwargs = kwargs
        
    def __call__(self, *args, **kwargs) -> T:
        return self._provides(*args, **kwargs, **self._provide_kwargs(**self.__kwargs))

