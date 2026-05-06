from datetime import date
from typing import Any, Dict

from models.reservation import Reservation

BASE_PRICE_PER_NIGHT = 300_000       # COP
EXTRA_GUEST_FEE_PER_NIGHT = 50_000  # COP por huésped adicional sobre el mínimo
BASE_GUESTS_INCLUDED = 2
CANCELLATION_FEE_RATE = 0.15         # 15% de penalización
LAST_MINUTE_THRESHOLD_DAYS = 7       # días para aplicar tarifa last-minute
LAST_MINUTE_MULTIPLIER = 1.20        # +20%


def recalculate_price(reservation: Reservation, changes: Dict[str, Any]) -> float:
    check_in = changes.get("new_check_in", reservation.check_in)
    check_out = changes.get("new_check_out", reservation.check_out)
    guests = changes.get("new_guests", reservation.guests)
    return _compute_price(check_in, check_out, guests)


def adjust_dates_price(check_in: date, check_out: date, guests: int) -> float:
    return _compute_price(check_in, check_out, guests)


def apply_extra_guest_fee(guests: int, nights: int) -> float:
    extra = max(0, guests - BASE_GUESTS_INCLUDED)
    return extra * EXTRA_GUEST_FEE_PER_NIGHT * nights


def calculate_cancellation_fee(reservation: Reservation) -> float:
    days_until = (reservation.check_in - date.today()).days
    if days_until >= LAST_MINUTE_THRESHOLD_DAYS:
        return reservation.total_price * CANCELLATION_FEE_RATE
    return reservation.total_price * 0.30  # 30% si es last-minute


def _compute_price(check_in: date, check_out: date, guests: int) -> float:
    nights = max(1, (check_out - check_in).days)
    base = nights * BASE_PRICE_PER_NIGHT
    extra_guests = apply_extra_guest_fee(guests, nights)

    subtotal = base + extra_guests

    days_until = (check_in - date.today()).days
    if 0 < days_until < LAST_MINUTE_THRESHOLD_DAYS:
        subtotal *= LAST_MINUTE_MULTIPLIER

    return round(subtotal, 2)


def price_breakdown(check_in: date, check_out: date, guests: int) -> Dict[str, Any]:
    nights = max(1, (check_out - check_in).days)
    base = nights * BASE_PRICE_PER_NIGHT
    extra = apply_extra_guest_fee(guests, nights)
    days_until = (check_in - date.today()).days
    last_minute = 0 < days_until < LAST_MINUTE_THRESHOLD_DAYS
    multiplier = LAST_MINUTE_MULTIPLIER if last_minute else 1.0
    total = round((base + extra) * multiplier, 2)

    return {
        "nights": nights,
        "base_price": base,
        "extra_guest_fee": extra,
        "last_minute_surcharge": round((base + extra) * (multiplier - 1), 2),
        "total": total,
        "last_minute_applied": last_minute,
    }
