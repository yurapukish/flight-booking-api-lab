"""ConnectionManager — тримає підписників і робить broadcast."""

from fastapi import WebSocket


class ConnectionManager:
    """Один dashboard на всіх. Кожен клієнт може мати свій фільтр подій.

    self.subscribers: dict[WebSocket, set[str]]
        ключ — підключення, значення — множина event-типів, які хоче клієнт.
        Порожня множина = «всі події» (default).
    """

    def __init__(self):
        self.subscribers: dict[WebSocket, set[str]] = {}

    def subscribe(self, ws: WebSocket):
        """Новий клієнт — без фільтра (бачить усе)."""
        self.subscribers[ws] = set()

    def unsubscribe(self, ws: WebSocket):
        self.subscribers.pop(ws, None)

    def set_filter(self, ws: WebSocket, event_types: set[str]):
        """Перевизначити фільтр для конкретного підписника."""
        if ws in self.subscribers:
            self.subscribers[ws] = event_types

    async def broadcast(self, event: dict):
        """Розіслати подію усім, у кого фільтр пропускає цей event-тип.

        Порожній фільтр = пропускати все. Мертві з'єднання — викидаємо.
        """
        dead = []
        for ws, filters in list(self.subscribers.items()):
            if filters and event["event"] not in filters:
                continue
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unsubscribe(ws)


manager = ConnectionManager()
