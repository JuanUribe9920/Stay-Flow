import json
import os
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


SYSTEM_PROMPT = """Eres un asistente especializado en gestión de reservas de alojamiento vacacional.
Analiza eventos de cambio o cancelación y devuelve una clasificación estructurada en JSON."""

CLASSIFICATION_PROMPT = """
Analiza este evento de reserva y responde ÚNICAMENTE con un JSON válido que tenga exactamente estas claves:
- "intent": "modify" | "cancel" | "inquiry"
- "priority": "low" | "medium" | "high"
- "recommendation": "approve" | "reject" | "review"
- "reasoning": string (explicación breve, máx 80 caracteres)
- "risk_score": número entre 0.0 y 1.0 (probabilidad de problema)

Evento: {description}
Tipo declarado: {event_type}

Responde SOLO con el JSON, sin markdown ni texto adicional.
"""


def classify_event(description: str, event_type: str = "change") -> Dict[str, Any]:
    if _OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        result = _classify_with_openai(description, event_type)
        if result:
            return result
    return _classify_with_rules(description, event_type)


def _classify_with_openai(description: str, event_type: str) -> Optional[Dict[str, Any]]:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": CLASSIFICATION_PROMPT.format(
                        description=description, event_type=event_type
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=250,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception:
        return None


def _classify_with_rules(description: str, event_type: str) -> Dict[str, Any]:
    text = description.lower()

    if event_type == "cancellation" or any(w in text for w in ["cancel", "baja", "anular"]):
        intent = "cancel"
        priority = "high"
        recommendation = "review"
        risk = 0.7
        reasoning = "Cancelación detectada — requiere revisión manual"
    elif any(w in text for w in ["huésped", "guest", "persona", "people", "adicional"]):
        intent = "modify"
        priority = "medium"
        recommendation = "approve"
        risk = 0.3
        reasoning = "Cambio de número de huéspedes — aprobación automática"
    elif any(w in text for w in ["fecha", "date", "check", "día", "semana"]):
        intent = "modify"
        priority = "medium"
        recommendation = "approve"
        risk = 0.35
        reasoning = "Cambio de fechas — verificar disponibilidad"
    else:
        intent = "modify"
        priority = "low"
        recommendation = "approve"
        risk = 0.1
        reasoning = "Cambio menor — aprobación automática (modo demo)"

    return {
        "intent": intent,
        "priority": priority,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "risk_score": risk,
        "mode": "rules-based",
    }


def generate_guest_message(context: Dict[str, Any]) -> str:
    if _OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        msg = _generate_message_openai(context, "huésped")
        if msg:
            return msg
    return _default_guest_message(context)


def generate_host_message(context: Dict[str, Any]) -> str:
    if _OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        msg = _generate_message_openai(context, "anfitrión")
        if msg:
            return msg
    return _default_host_message(context)


def _generate_message_openai(context: Dict[str, Any], recipient: str) -> Optional[str]:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"""
Genera un mensaje breve y profesional para el {recipient} de una reserva de alojamiento.
Contexto: {json.dumps(context, ensure_ascii=False, default=str)}

Requisitos:
- Máximo 3 oraciones
- Tono cálido pero profesional
- En español
- No uses markdown
- Incluye el ID de reserva
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _default_guest_message(ctx: Dict[str, Any]) -> str:
    rid = ctx.get("reservation_id", "N/A")
    status = ctx.get("action", "actualizada")
    price = ctx.get("new_price", 0)
    return (
        f"Estimado/a huésped, tu reserva {rid} ha sido {status} exitosamente. "
        f"El nuevo precio total es ${price:,.0f} COP. "
        "Gracias por elegir nuestro alojamiento."
    )


def _default_host_message(ctx: Dict[str, Any]) -> str:
    rid = ctx.get("reservation_id", "N/A")
    action = ctx.get("action", "modificada")
    guest = ctx.get("guest_name", "el huésped")
    return (
        f"La reserva {rid} de {guest} ha sido {action}. "
        f"Revisa el panel de StayFlow AI para más detalles."
    )
