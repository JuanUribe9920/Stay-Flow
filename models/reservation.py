from dataclasses import dataclass, field
from datetime import date
from typing import Literal
import uuid


@dataclass
class Reservation:
    id: str
    property: str
    guest_name: str
    check_in: date
    check_out: date
    guests: int
    status: Literal["active", "modified", "cancelled"]
    total_price: float
    guest_email: str = ""
    guest_phone: str = ""

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    @classmethod
    def create(
        cls,
        property: str,
        guest_name: str,
        check_in: date,
        check_out: date,
        guests: int,
        total_price: float,
        guest_email: str = "",
        guest_phone: str = "",
    ) -> "Reservation":
        return cls(
            id=f"RES-{str(uuid.uuid4())[:8].upper()}",
            property=property,
            guest_name=guest_name,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            status="active",
            total_price=total_price,
            guest_email=guest_email,
            guest_phone=guest_phone,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "property": self.property,
            "guest_name": self.guest_name,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "guests": self.guests,
            "status": self.status,
            "total_price": self.total_price,
            "guest_email": self.guest_email,
            "guest_phone": self.guest_phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Reservation":
        return cls(**data)
