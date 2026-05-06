from datetime import date
from typing import Any, Dict, List


def validate_dates(check_in: date, check_out: date) -> List[str]:
    errors = []
    if check_in >= check_out:
        errors.append("La fecha de check-out debe ser posterior al check-in.")
    if check_in < date.today():
        errors.append("La fecha de check-in no puede ser en el pasado.")
    nights = (check_out - check_in).days
    if nights > 90:
        errors.append("La estadía no puede superar 90 noches.")
    return errors


def validate_guests(guests: int, max_guests: int = 12) -> List[str]:
    errors = []
    if guests < 1:
        errors.append("El número de huéspedes debe ser al menos 1.")
    if guests > max_guests:
        errors.append(f"El número máximo de huéspedes permitido es {max_guests}.")
    return errors


def validate_reservation_change(reservation_id: str, changes: Dict[str, Any]) -> List[str]:
    errors = []
    if not reservation_id:
        errors.append("Se requiere un ID de reserva.")
    if not changes:
        errors.append("Debe especificar al menos un cambio.")
    return errors


def validate_cancellation(reservation_id: str, check_in: date) -> List[str]:
    errors = []
    if not reservation_id:
        errors.append("Se requiere un ID de reserva.")
    days_until_checkin = (check_in - date.today()).days
    if days_until_checkin < 0:
        errors.append("No se puede cancelar una reserva cuyo check-in ya ocurrió.")
    return errors
