from typing import Any, Callable, Coroutine

Handler = Callable[[int, Any, int], Coroutine[None, None, None]]


class Dispatcher:
    def __init__(self) -> None:
        self._channel_handlers: dict[str, Handler] = {}
        self._dispatch_id: int = 0

    def add_channel_handler(self, channels: list[str], handler: Handler) -> None:
        for channel in channels:
            self._channel_handlers[channel] = handler

    def remove_channel_handler(self, channels: list[str]) -> None:
        for channel in channels:
            if channel in self._channel_handlers:
                del self._channel_handlers[channel]

    async def dispatch(self, id: int, channel: str, data: Any) -> None:
        handler = self._channel_handlers.get(channel)

        if handler is None:
            return

        self._dispatch_id += 1

        await handler(id, data, self._dispatch_id)
