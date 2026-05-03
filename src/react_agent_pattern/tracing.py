from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    name: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time)


@dataclass
class Trace:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    events: list[TraceEvent] = field(default_factory=list)

    def add(self, name: str, **payload: Any) -> None:
        self.events.append(TraceEvent(name=name, payload=payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "events": [
                {"name": event.name, "timestamp": event.timestamp, "payload": event.payload}
                for event in self.events
            ],
        }

