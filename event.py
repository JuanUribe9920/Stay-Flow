from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal
import uuid


@dataclass
class Event:
    id: str
    type: Literal["change", "cancellation"]
    reservation_id: str
    payload: Dict[str, Any]
    status: Literal["pending", "processed"]
    created_at: datetime
    result: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        type: Literal["change", "cancellation"],
        reservation_id: str,
        payload: Dict[str, Any],
    ) -> "Event":
        return cls(
            id=f"EVT-{str(uuid.uuid4())[:8].upper()}",
            type=type,
            reservation_id=reservation_id,
            payload=payload,
            status="pending",
            created_at=datetime.now(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "reservation_id": self.reservation_id,
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(**data)
