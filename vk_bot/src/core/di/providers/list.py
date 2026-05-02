from typing import Any, Iterable

from .provider import Provider


class List(Provider[list[Any]]):
    _provides: list[Any]

    def __init__(self, *provides: Iterable[Any]):
        super().__init__(list(provides))

    def __call__(self) -> list[Any]:
        return self._provide_args(*self._provides)
