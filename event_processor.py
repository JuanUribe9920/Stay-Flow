from datetime import date
from typing import Any, Dict, List, Tuple

from models.event import Event
from models.reservation import Reservation
from services.notification_service import dispatch_notifications
from services.pricing_engine import recalculate_price, price_breakdown
from utils.ai_classifier import classify_event
from utils.validators import (
    validate_dates,
    validate_guests,
    validate_reservation_change,
    validate_cancellation,
)


def create_event(
    reservation_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> Event:
    return Event.create(event_type, reservation_id, payload)


def process_event(
    event: Event,
    reservation: Reservation,
) -> Tuple[Reservation, Dict[str, Any]]:
    """
    Full pipeline: validate → classify → apply business rules → recalculate price
    → generate messages → send notifications.
    Returns updated reservation and a result dict.
    """
    # 1. Validate
    errors = _validate_event(event, reservation)
    if errors:
        return reservation, {"success": False, "errors": errors}

    # 2. Classify with AI
    description = _build_description(event, reservation)
    classification = classify_event(description, event.type)

    # 3. Business rules — reject if AI says so
    if classification.get("recommendation") == "reject":
        event.status = "processed"
        event.result = {"rejected": True, "classification": classification}
        return reservation, {
            "success": False,
            "classification": classification,
            "errors": ["Cambio rechazado por las reglas de negocio."],
        }

    # 4. Apply changes to reservation
    updated_reservation = _apply_changes(reservation, event)

    # 5. Recalculate price
    new_price = recalculate_price(updated_reservation, event.payload)
    updated_reservation.total_price = new_price
    breakdown = price_breakdown(
        updated_reservation.check_in,
        updated_reservation.check_out,
        updated_reservation.guests,
    )

    # 6. Build notification context
    action_label = "cancelada" if event.type == "cancellation" else "modificada"
    context = {
        "reservation_id": updated_reservation.id,
        "guest_name": updated_reservation.guest_name,
        "guest_email": updated_reservation.guest_email,
        "guest_phone": updated_reservation.guest_phone,
        "property": updated_reservation.property,
        "action": action_label,
        "new_price": new_price,
        "changes": event.payload,
        "classification": classification,
    }

    # 7. Generate messages and send notifications
    notifications = dispatch_notifications(context)

    event.status = "processed"
    event.result = {
        "classification": classification,
        "new_price": new_price,
        "notifications": {
            "email": notifications["email"],
            "whatsapp": notifications["whatsapp"],
        },
    }

    return updated_reservation, {
        "success": True,
        "classification": classification,
        "new_price": new_price,
        "price_breakdown": breakdown,
        "guest_message": notifications["guest_message"],
        "host_message": notifications["host_message"],
        "notifications": {
            "email": notifications["email"],
            "whatsapp": notifications["whatsapp"],
        },
        "reservation": updated_reservation,
    }


def _validate_event(event: Event, reservation: Reservation) -> List[str]:
    errors: List[str] = []

    if event.type == "cancellation":
        errors += validate_cancellation(reservation.id, reservation.check_in)
        return errors

    # Date validation
    new_check_in = event.payload.get("new_check_in", reservation.check_in)
    new_check_out = event.payload.get("new_check_out", reservation.check_out)
    if new_check_in != reservation.check_in or new_check_out != reservation.check_out:
        errors += validate_dates(new_check_in, new_check_out)

    # Guest validation
    if "new_guests" in event.payload:
        errors += validate_guests(event.payload["new_guests"])

    if not event.payload:
        errors.append("El payload del evento está vacío.")

    return errors


def _apply_changes(reservation: Reservation, event: Event) -> Reservation:
    import copy
    updated = copy.copy(reservation)

    if event.type == "cancellation":
        updated.status = "cancelled"
        return updated

    payload = event.payload
    if "new_check_in" in payload:
        updated.check_in = payload["new_check_in"]
    if "new_check_out" in payload:
        updated.check_out = payload["new_check_out"]
    if "new_guests" in payload:
        updated.guests = payload["new_guests"]
    updated.status = "modified"
    return updated


def _build_description(event: Event, reservation: Reservation) -> str:
    parts = [
        f"Reserva {reservation.id} de {reservation.guest_name}",
        f"en {reservation.property}.",
        f"Evento: {event.type}.",
    ]
    p = event.payload
    if "new_check_in" in p or "new_check_out" in p:
        parts.append(
            f"Nuevas fechas: {p.get('new_check_in', reservation.check_in)} "
            f"a {p.get('new_check_out', reservation.check_out)}."
        )
    if "new_guests" in p:
        parts.append(
            f"Cambio de {reservation.guests} a {p['new_guests']} huéspedes."
        )
    return " ".join(parts)
