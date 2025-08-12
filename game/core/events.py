from typing import Callable, Dict, List, Any


class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, topic: str, fn: Callable[[Dict[str, Any]], None]):
        self._subs.setdefault(topic, []).append(fn)

    def publish(self, topic: str, payload: Dict[str, Any]):
        for fn in self._subs.get(topic, []):
            fn(payload)
