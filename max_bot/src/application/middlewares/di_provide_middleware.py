from typing import Any, Awaitable, Callable, Dict
from maxapi.filters.middleware import BaseMiddleware
from maxapi.types import UpdateUnion


class DIProvideMiddleware(BaseMiddleware):
    container = None

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event_object: UpdateUnion,
        data: Dict[str, Any],
    ) -> Any:
        if self.container:
            data.update(self.container.providers)
        return await handler(event_object, data)
