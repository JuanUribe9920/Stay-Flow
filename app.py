import os
import sys
from datetime import date, timedelta, datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from models.event import Event
from models.reservation import Reservation
from services.event_processor import create_event, process_event
from services.pricing_engine import adjust_dates_price, price_breakdown
from utils.validators import validate_dates, validate_guests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="StayFlow AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* ── Base ── */
.stApp { background-color: #0B0F1A; }
html, body { font-family: 'Inter', 'Segoe UI', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0E1420 !important;
    border-right: 1px solid #1E2D45;
}
[data-testid="stSidebar"] * { color: #C8D0DC !important; }
[data-testid="stSidebarNav"] { display: none; }

/* ── Hide streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stHeader"] {
    visibility: hidden;
    height: 0px !important;
    min-height: 0 !important;
    padding: 0 !important;
}

/* ── Custom sidebar tab (injected via JS) ── */
#sf-sidebar-tab {
    position: fixed;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    background: #121826;
    border: 1px solid #00FFD180;
    border-left: none;
    border-radius: 0 10px 10px 0;
    width: 26px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 99999;
    color: #00FFD1;
    font-size: 18px;
    font-weight: 900;
    box-shadow: 4px 0 16px #00000080;
    transition: width 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
    user-select: none;
}
#sf-sidebar-tab:hover {
    width: 34px;
    background: #1A3045;
    border-color: #00FFD1;
    box-shadow: 4px 0 20px #00FFD140;
}

/* ── Cards ── */
.sf-card {
    background: #121826;
    border: 1px solid #1E2D45;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 16px;
}
.sf-card-accent {
    background: #0D1E30;
    border: 1px solid #00FFD1;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 16px;
}

/* ── Metric cards ── */
.sf-metric {
    background: #121826;
    border: 1px solid #1E2D45;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: border-color 0.2s;
}
.sf-metric:hover { border-color: #00FFD1; }
.sf-metric-value {
    font-size: 2.1em;
    font-weight: 800;
    color: #00FFD1;
    line-height: 1.1;
}
.sf-metric-label {
    font-size: 0.78em;
    color: #6B7A93;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-top: 4px;
}
.sf-metric-delta {
    font-size: 0.85em;
    color: #00FFD1;
    margin-top: 2px;
}

/* ── Logo ── */
.sf-logo {
    font-size: 1.35em;
    font-weight: 900;
    color: #00FFD1;
    letter-spacing: 3px;
    text-transform: uppercase;
}
.sf-tagline { font-size: 0.72em; color: #4A5568; letter-spacing: 1px; }

/* ── Section headers ── */
.sf-section-title {
    font-size: 1.4em;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 4px;
}
.sf-section-sub { font-size: 0.85em; color: #6B7A93; margin-bottom: 20px; }

/* ── Badges ── */
.badge {
    display: inline-block;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75em;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.badge-active   { background: #00FFD115; color: #00FFD1; border: 1px solid #00FFD1; }
.badge-modified { background: #F59E0B15; color: #F59E0B; border: 1px solid #F59E0B; }
.badge-cancelled{ background: #EF444415; color: #EF4444; border: 1px solid #EF4444; }
.badge-pending  { background: #6366F115; color: #818CF8; border: 1px solid #6366F1; }
.badge-processed{ background: #10B98115; color: #34D399; border: 1px solid #10B981; }

/* ── Priority badges ── */
.priority-low    { color: #6B7A93; }
.priority-medium { color: #F59E0B; }
.priority-high   { color: #EF4444; }

/* ── Result box ── */
.sf-result {
    background: #081420;
    border: 1px solid #00FFD1;
    border-radius: 10px;
    padding: 18px 20px;
    margin: 10px 0;
}
.sf-result-error {
    background: #1A0A0A;
    border: 1px solid #EF4444;
    border-radius: 10px;
    padding: 18px 20px;
    margin: 10px 0;
}

/* ── Message box ── */
.sf-message {
    background: #0E1A2A;
    border-left: 3px solid #00FFD1;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    margin: 8px 0;
    font-size: 0.9em;
    color: #C8D0DC;
    line-height: 1.6;
}
.sf-message-host {
    background: #1A1020;
    border-left: 3px solid #818CF8;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    margin: 8px 0;
    font-size: 0.9em;
    color: #C8D0DC;
    line-height: 1.6;
}

/* ── AI classification box ── */
.ai-box {
    background: #0A1628;
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}
.ai-chip {
    background: #112240;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8em;
    color: #CBD5E1;
}
.ai-chip span { color: #00FFD1; font-weight: 700; }

/* ── Divider ── */
.sf-divider {
    border: none;
    border-top: 1px solid #1E2D45;
    margin: 20px 0;
}

/* ── Nav button ── */
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    display: block;
}

/* ── Buttons ── */
.stButton > button {
    background: #00FFD1 !important;
    color: #0B0F1A !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    letter-spacing: 0.5px;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #00E6BB !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px #00FFD140;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea {
    background: #0E1520 !important;
    border: 1px solid #1E2D45 !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
}
.stDateInput > div > div > input {
    background: #0E1520 !important;
    border: 1px solid #1E2D45 !important;
    color: #FFFFFF !important;
}
.stSelectbox > div > div {
    background: #0E1520 !important;
    border: 1px solid #1E2D45 !important;
    color: #FFFFFF !important;
}

/* ── Streamlit metric override ── */
[data-testid="metric-container"] {
    background: #121826;
    border: 1px solid #1E2D45;
    border-radius: 12px;
    padding: 16px;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #121826 !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Inject JS sidebar tab — works regardless of Streamlit's internal selectors
SIDEBAR_JS = """
<script>
(function () {
    function findSidebarToggle() {
        // Try all known selectors across Streamlit versions
        return (
            document.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
            document.querySelector('[data-testid="collapsedControl"] button') ||
            document.querySelector('button[aria-label*="sidebar" i]') ||
            document.querySelector('button[aria-label*="menu" i]') ||
            document.querySelector('section[data-testid="stSidebar"] ~ button') ||
            null
        );
    }

    function isSidebarCollapsed() {
        const sb = document.querySelector('[data-testid="stSidebar"]');
        if (!sb) return false;
        const w = sb.getBoundingClientRect().width;
        return w < 80;
    }

    function toggleSidebar() {
        const btn = findSidebarToggle();
        if (btn) {
            btn.click();
        } else {
            // Direct manipulation: find and toggle the sidebar container
            const sb = document.querySelector('[data-testid="stSidebar"]');
            if (sb) {
                // Trigger a synthetic click on the sidebar area
                const clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                const toggleBtn = sb.querySelector('button') || sb.parentElement?.querySelector('button');
                if (toggleBtn) toggleBtn.click();
            }
        }
    }

    function ensureTab() {
        let tab = document.getElementById('sf-sidebar-tab');

        if (isSidebarCollapsed()) {
            if (!tab) {
                tab = document.createElement('div');
                tab.id = 'sf-sidebar-tab';
                tab.title = 'Abrir menú';
                tab.innerHTML = '&#8250;';
                tab.addEventListener('click', toggleSidebar);
                document.body.appendChild(tab);
            }
            tab.style.display = 'flex';
        } else {
            if (tab) tab.style.display = 'none';
        }
    }

    // Poll every 250ms — lightweight, works on all Streamlit versions
    setInterval(ensureTab, 250);
})();
</script>
"""
st.markdown(SIDEBAR_JS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SAMPLE DATA
# ─────────────────────────────────────────────
SAMPLE_RESERVATIONS = [
    {
        "id": "RES-001",
        "property": "Apartamento El Poblado",
        "guest_name": "Carlos Restrepo",
        "check_in": date(2026, 5, 10),
        "check_out": date(2026, 5, 14),
        "guests": 2,
        "status": "active",
        "total_price": 1_200_000,
        "guest_email": "carlos@example.com",
        "guest_phone": "+573001234567",
    },
    {
        "id": "RES-002",
        "property": "Casa Laureles",
        "guest_name": "Valentina Torres",
        "check_in": date(2026, 5, 15),
        "check_out": date(2026, 5, 20),
        "guests": 4,
        "status": "active",
        "total_price": 1_800_000,
        "guest_email": "valen@example.com",
        "guest_phone": "+573109876543",
    },
    {
        "id": "RES-003",
        "property": "Penthouse Santa Fe",
        "guest_name": "Andrés Gómez",
        "check_in": date(2026, 4, 20),
        "check_out": date(2026, 4, 24),
        "guests": 3,
        "status": "modified",
        "total_price": 1_650_000,
        "guest_email": "andres@example.com",
        "guest_phone": "+573151112233",
    },
    {
        "id": "RES-004",
        "property": "Loft Ciudad del Río",
        "guest_name": "Mariana Silva",
        "check_in": date(2026, 4, 10),
        "check_out": date(2026, 4, 12),
        "guests": 2,
        "status": "cancelled",
        "total_price": 600_000,
        "guest_email": "mariana@example.com",
        "guest_phone": "+573205554433",
    },
    {
        "id": "RES-005",
        "property": "Apartamento El Poblado",
        "guest_name": "Felipe Rodríguez",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 7),
        "guests": 2,
        "status": "active",
        "total_price": 1_800_000,
        "guest_email": "felipe@example.com",
        "guest_phone": "+573301234567",
    },
    {
        "id": "RES-006",
        "property": "Casa Laureles",
        "guest_name": "Daniela Castro",
        "check_in": date(2026, 3, 15),
        "check_out": date(2026, 3, 18),
        "guests": 3,
        "status": "modified",
        "total_price": 1_050_000,
        "guest_email": "dani@example.com",
        "guest_phone": "+573401234567",
    },
]

SAMPLE_EVENTS = [
    {
        "id": "EVT-001",
        "type": "change",
        "reservation_id": "RES-003",
        "payload": {"new_guests": 3},
        "status": "processed",
        "created_at": datetime(2026, 4, 18, 10, 30),
        "result": {"classification": {"intent": "modify", "priority": "medium", "recommendation": "approve"}},
    },
    {
        "id": "EVT-002",
        "type": "cancellation",
        "reservation_id": "RES-004",
        "payload": {"reason": "personal"},
        "status": "processed",
        "created_at": datetime(2026, 4, 8, 14, 0),
        "result": {"classification": {"intent": "cancel", "priority": "high", "recommendation": "review"}},
    },
    {
        "id": "EVT-003",
        "type": "change",
        "reservation_id": "RES-006",
        "payload": {"new_guests": 3, "new_check_out": date(2026, 3, 18)},
        "status": "processed",
        "created_at": datetime(2026, 3, 12, 9, 15),
        "result": {"classification": {"intent": "modify", "priority": "low", "recommendation": "approve"}},
    },
]

REVENUE_SERIES = {
    "Ene": 3_200_000,
    "Feb": 4_100_000,
    "Mar": 3_800_000,
    "Abr": 5_200_000,
    "May": 4_650_000,
    "Jun": 1_800_000,
}


def init_state():
    if "reservations" not in st.session_state:
        st.session_state.reservations: Dict[str, dict] = {
            r["id"]: r for r in SAMPLE_RESERVATIONS
        }
    if "events" not in st.session_state:
        st.session_state.events: List[dict] = SAMPLE_EVENTS
    if "sim_result" not in st.session_state:
        st.session_state.sim_result = None


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
STATUS_BADGE = {
    "active":    '<span class="badge badge-active">● Activa</span>',
    "modified":  '<span class="badge badge-modified">◎ Modificada</span>',
    "cancelled": '<span class="badge badge-cancelled">✕ Cancelada</span>',
}
EVENT_BADGE = {
    "pending":   '<span class="badge badge-pending">⏳ Pendiente</span>',
    "processed": '<span class="badge badge-processed">✓ Procesado</span>',
}
PRIORITY_COLOR = {"low": "#6B7A93", "medium": "#F59E0B", "high": "#EF4444"}
RECOMMEND_COLOR = {"approve": "#00FFD1", "review": "#F59E0B", "reject": "#EF4444"}


def fmt_cop(value: float) -> str:
    return f"${value:,.0f}"


def occupancy_rate(reservations: dict) -> float:
    today = date.today()
    month_start = today.replace(day=1)
    next_month = (month_start.replace(month=month_start.month % 12 + 1)
                  if month_start.month < 12
                  else month_start.replace(year=month_start.year + 1, month=1))
    month_nights = (next_month - month_start).days
    booked = set()
    for r in reservations.values():
        if r["status"] == "cancelled":
            continue
        ci, co = r["check_in"], r["check_out"]
        d = ci
        while d < co:
            if month_start <= d < next_month:
                booked.add(d)
            d += timedelta(days=1)
    return (len(booked) / month_nights) * 100 if month_nights else 0


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="sf-logo">StayFlow AI</div>'
            '<div class="sf-tagline">RENTAL AUTOMATION</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<hr class='sf-divider'>", unsafe_allow_html=True)

        page = st.radio(
            "Navegación",
            ["Dashboard", "Reservas", "Eventos", "Simulador de Cambios"],
            label_visibility="collapsed",
        )

        st.markdown("<hr class='sf-divider'>", unsafe_allow_html=True)

        # API key status
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        if has_key:
            st.markdown("🟢 **OpenAI** conectado")
        else:
            st.markdown("🟡 **Modo Demo** — sin API key")
            with st.expander("¿Cómo configurar?"):
                st.code("OPENAI_API_KEY=sk-...", language="bash")
                st.caption("Crea un archivo `.env` en la raíz del proyecto.")

        st.markdown("<br>", unsafe_allow_html=True)
        total_res = len(st.session_state.reservations)
        active_res = sum(1 for r in st.session_state.reservations.values() if r["status"] == "active")
        st.caption(f"📋 {total_res} reservas · {active_res} activas")
        st.caption(f"⚡ {len(st.session_state.events)} eventos procesados")

    return page


# ─────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────
def page_dashboard():
    st.markdown(
        '<div class="sf-section-title">Dashboard</div>'
        '<div class="sf-section-sub">Vista general del rendimiento de tus propiedades</div>',
        unsafe_allow_html=True,
    )

    reservations = st.session_state.reservations
    events = st.session_state.events

    total_revenue = sum(r["total_price"] for r in reservations.values() if r["status"] != "cancelled")
    active_count = sum(1 for r in reservations.values() if r["status"] == "active")
    cancelled_count = sum(1 for r in reservations.values() if r["status"] == "cancelled")
    occ = occupancy_rate(reservations)

    # ── Metric row ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="sf-metric">'
            f'<div class="sf-metric-value">{fmt_cop(total_revenue)}</div>'
            f'<div class="sf-metric-label">Ingresos Totales</div>'
            f'<div class="sf-metric-delta">↑ COP</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="sf-metric">'
            f'<div class="sf-metric-value">{occ:.0f}%</div>'
            f'<div class="sf-metric-label">Ocupación del Mes</div>'
            f'<div class="sf-metric-delta">Noches reservadas</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="sf-metric">'
            f'<div class="sf-metric-value">{active_count}</div>'
            f'<div class="sf-metric-label">Reservas Activas</div>'
            f'<div class="sf-metric-delta">En el sistema</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="sf-metric">'
            f'<div class="sf-metric-value">{cancelled_count}</div>'
            f'<div class="sf-metric-label">Cancelaciones</div>'
            f'<div class="sf-metric-delta">Este período</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Revenue chart ──
    col_chart, col_props = st.columns([2, 1])

    with col_chart:
        st.markdown(
            '<div class="sf-card">'
            "<b style='color:#FFFFFF'>Ingresos por Mes (COP)</b>",
            unsafe_allow_html=True,
        )
        df_rev = pd.DataFrame(
            {"Ingresos": REVENUE_SERIES}
        )
        st.line_chart(df_rev, color="#00FFD1", height=220)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_props:
        st.markdown(
            '<div class="sf-card"><b style="color:#FFFFFF">Propiedades</b><br><br>',
            unsafe_allow_html=True,
        )
        props: Dict[str, Dict] = {}
        for r in reservations.values():
            p = r["property"]
            if p not in props:
                props[p] = {"activas": 0, "ingresos": 0}
            if r["status"] != "cancelled":
                props[p]["activas"] += 1
                props[p]["ingresos"] += r["total_price"]

        for prop, data in props.items():
            short = prop[:22] + "…" if len(prop) > 22 else prop
            st.markdown(
                f"<b style='color:#C8D0DC'>{short}</b><br>"
                f"<span style='color:#6B7A93;font-size:.8em'>"
                f"Activas: {data['activas']} &nbsp;·&nbsp; "
                f"{fmt_cop(data['ingresos'])}</span><br><br>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Recent events ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<b style='color:#FFFFFF'>Eventos Recientes</b>",
        unsafe_allow_html=True,
    )
    recent = sorted(events, key=lambda e: e["created_at"], reverse=True)[:5]
    for ev in recent:
        r = reservations.get(ev["reservation_id"], {})
        guest = r.get("guest_name", "Desconocido")
        prop = r.get("property", ev["reservation_id"])[:30]
        status_badge = EVENT_BADGE.get(ev["status"], "")
        ev_label = "🔄 Modificación" if ev["type"] == "change" else "❌ Cancelación"
        ts = ev["created_at"].strftime("%d %b · %H:%M") if isinstance(ev["created_at"], datetime) else str(ev["created_at"])
        classification = ev.get("result", {}).get("classification", {})
        prio = classification.get("priority", "—")
        prio_color = PRIORITY_COLOR.get(prio, "#6B7A93")
        st.markdown(
            f'<div class="sf-card" style="padding:14px 18px;margin-bottom:8px">'
            f"<span style='color:#FFFFFF'>{ev_label} &nbsp; {ev['id']}</span> &nbsp; {status_badge}"
            f"<span style='float:right;color:#6B7A93;font-size:.8em'>{ts}</span><br>"
            f"<span style='color:#6B7A93;font-size:.85em'>{guest} · {prop}</span>"
            f"<span style='float:right;color:{prio_color};font-size:.8em;font-weight:700'>"
            f"Prioridad: {prio.upper()}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# PAGE: RESERVAS
# ─────────────────────────────────────────────
def page_reservations():
    st.markdown(
        '<div class="sf-section-title">Reservas</div>'
        '<div class="sf-section-sub">Gestión y detalle de todas las reservas</div>',
        unsafe_allow_html=True,
    )

    reservations = st.session_state.reservations

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("🔍 Buscar por huésped o propiedad", placeholder="Ej: Carlos, El Poblado…")
    with col_f2:
        status_filter = st.selectbox("Estado", ["Todos", "active", "modified", "cancelled"])
    with col_f3:
        prop_options = ["Todas"] + sorted({r["property"] for r in reservations.values()})
        prop_filter = st.selectbox("Propiedad", prop_options)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter data
    filtered = list(reservations.values())
    if search:
        s = search.lower()
        filtered = [r for r in filtered if s in r["guest_name"].lower() or s in r["property"].lower()]
    if status_filter != "Todos":
        filtered = [r for r in filtered if r["status"] == status_filter]
    if prop_filter != "Todas":
        filtered = [r for r in filtered if r["property"] == prop_filter]

    st.caption(f"{len(filtered)} reserva(s) encontrada(s)")

    for res in sorted(filtered, key=lambda r: r["check_in"], reverse=True):
        nights = (res["check_out"] - res["check_in"]).days
        badge = STATUS_BADGE.get(res["status"], "")
        with st.expander(f"{res['id']} — {res['guest_name']} · {res['property']}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(
                    f"**Huésped:** {res['guest_name']}<br>"
                    f"**Propiedad:** {res['property']}<br>"
                    f"**Email:** {res['guest_email'] or '—'}<br>"
                    f"**Teléfono:** {res['guest_phone'] or '—'}",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"**Check-in:** {res['check_in'].strftime('%d %b %Y')}<br>"
                    f"**Check-out:** {res['check_out'].strftime('%d %b %Y')}<br>"
                    f"**Noches:** {nights}<br>"
                    f"**Huéspedes:** {res['guests']}",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"**Estado:**<br>{badge}<br><br>"
                    f"**Total:**<br>"
                    f"<span style='color:#00FFD1;font-size:1.3em;font-weight:800'>"
                    f"{fmt_cop(res['total_price'])}</span>",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────
# PAGE: EVENTOS
# ─────────────────────────────────────────────
def page_events():
    st.markdown(
        '<div class="sf-section-title">Eventos</div>'
        '<div class="sf-section-sub">Historial de cambios y cancelaciones procesadas por el sistema</div>',
        unsafe_allow_html=True,
    )

    events = st.session_state.events
    reservations = st.session_state.reservations

    if not events:
        st.info("No hay eventos registrados aún. Usa el Simulador para generar uno.")
        return

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    total_ev = len(events)
    processed = sum(1 for e in events if e["status"] == "processed")
    cancellations = sum(1 for e in events if e["type"] == "cancellation")
    with c1:
        st.markdown(f'<div class="sf-metric"><div class="sf-metric-value">{total_ev}</div><div class="sf-metric-label">Total Eventos</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="sf-metric"><div class="sf-metric-value">{processed}</div><div class="sf-metric-label">Procesados</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="sf-metric"><div class="sf-metric-value">{cancellations}</div><div class="sf-metric-label">Cancelaciones</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    for ev in sorted(events, key=lambda e: e["created_at"], reverse=True):
        res = reservations.get(ev["reservation_id"], {})
        guest = res.get("guest_name", ev["reservation_id"])
        prop = res.get("property", "—")
        status_badge = EVENT_BADGE.get(ev["status"], "")
        ev_icon = "🔄" if ev["type"] == "change" else "❌"
        ev_type_label = "Modificación" if ev["type"] == "change" else "Cancelación"
        ts = (ev["created_at"].strftime("%d %b %Y · %H:%M")
              if isinstance(ev["created_at"], datetime) else str(ev["created_at"]))

        classification = ev.get("result", {}).get("classification", {})
        intent = classification.get("intent", "—")
        prio = classification.get("priority", "—")
        rec = classification.get("recommendation", "—")
        prio_color = PRIORITY_COLOR.get(prio, "#6B7A93")
        rec_color = RECOMMEND_COLOR.get(rec, "#6B7A93")

        with st.expander(f"{ev_icon} {ev['id']} — {ev_type_label} · {guest}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"**ID Evento:** `{ev['id']}`<br>"
                    f"**Reserva:** `{ev['reservation_id']}`<br>"
                    f"**Huésped:** {guest}<br>"
                    f"**Propiedad:** {prop}<br>"
                    f"**Fecha:** {ts}<br>"
                    f"**Estado:** {status_badge}",
                    unsafe_allow_html=True,
                )
            with col2:
                if classification:
                    st.markdown(
                        f"**Clasificación IA:**<br>"
                        f"Intent: <span style='color:#00FFD1'>{intent}</span><br>"
                        f"Prioridad: <span style='color:{prio_color}'>{prio.upper()}</span><br>"
                        f"Recomendación: <span style='color:{rec_color}'>{rec.upper()}</span>",
                        unsafe_allow_html=True,
                    )
                if ev.get("payload"):
                    st.markdown("**Payload:**")
                    st.json(ev["payload"])


# ─────────────────────────────────────────────
# PAGE: SIMULADOR
# ─────────────────────────────────────────────
def page_simulator():
    st.markdown(
        '<div class="sf-section-title">Simulador de Cambios</div>'
        '<div class="sf-section-sub">Procesa modificaciones y cancelaciones a través del pipeline completo de IA</div>',
        unsafe_allow_html=True,
    )

    reservations = st.session_state.reservations
    active_res = {
        k: v for k, v in reservations.items() if v["status"] != "cancelled"
    }

    if not active_res:
        st.warning("No hay reservas activas para modificar.")
        return

    # ── Step 1: Select reservation ──
    st.markdown("### Paso 1 — Selecciona la Reserva")
    res_options = {
        f"{v['id']} · {v['guest_name']} · {v['property']}": k
        for k, v in active_res.items()
    }
    selected_label = st.selectbox("Reserva", list(res_options.keys()))
    selected_id = res_options[selected_label]
    res = reservations[selected_id]

    # Show current state
    col_ci, col_co, col_g, col_p = st.columns(4)
    col_ci.metric("Check-in actual", res["check_in"].strftime("%d %b %Y"))
    col_co.metric("Check-out actual", res["check_out"].strftime("%d %b %Y"))
    col_g.metric("Huéspedes", res["guests"])
    col_p.metric("Precio actual", fmt_cop(res["total_price"]))

    st.markdown("<hr class='sf-divider'>", unsafe_allow_html=True)

    # ── Step 2: Event type ──
    st.markdown("### Paso 2 — Tipo de Cambio")
    event_type = st.radio(
        "¿Qué deseas hacer?",
        ["Modificar fechas", "Modificar huéspedes", "Modificar fechas y huéspedes", "Cancelar reserva"],
        horizontal=True,
    )

    st.markdown("<hr class='sf-divider'>", unsafe_allow_html=True)

    # ── Step 3: Inputs ──
    st.markdown("### Paso 3 — Nuevos Valores")
    payload: Dict[str, Any] = {}

    if event_type in ("Modificar fechas", "Modificar fechas y huéspedes"):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            new_ci = st.date_input("Nueva fecha de check-in", value=res["check_in"])
        with col_d2:
            new_co = st.date_input("Nueva fecha de check-out", value=res["check_out"])
        payload["new_check_in"] = new_ci
        payload["new_check_out"] = new_co

    if event_type in ("Modificar huéspedes", "Modificar fechas y huéspedes"):
        new_guests = st.number_input(
            "Nuevo número de huéspedes",
            min_value=1, max_value=12,
            value=res["guests"],
            step=1,
        )
        payload["new_guests"] = int(new_guests)

    if event_type == "Cancelar reserva":
        st.markdown(
            '<div class="sf-result-error">'
            "⚠️ <b style='color:#EF4444'>Esta acción cancelará la reserva definitivamente.</b><br>"
            "<span style='color:#C8D0DC;font-size:.9em'>El sistema aplicará la política de cancelación y notificará al huésped.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        payload["reason"] = "user_request"
        api_event_type = "cancellation"
    else:
        api_event_type = "change"

    # Live price preview
    if api_event_type == "change" and payload:
        check_in_preview = payload.get("new_check_in", res["check_in"])
        check_out_preview = payload.get("new_check_out", res["check_out"])
        guests_preview = payload.get("new_guests", res["guests"])

        if check_in_preview < check_out_preview:
            bd = price_breakdown(check_in_preview, check_out_preview, guests_preview)
            st.markdown(
                f'<div class="sf-card">'
                f"<b style='color:#FFFFFF'>Precio Estimado</b><br><br>"
                f"<span style='color:#6B7A93'>Base ({bd['nights']} noches):</span> "
                f"<span style='color:#C8D0DC'>{fmt_cop(bd['base_price'])}</span><br>"
                f"<span style='color:#6B7A93'>Huéspedes extra:</span> "
                f"<span style='color:#C8D0DC'>{fmt_cop(bd['extra_guest_fee'])}</span><br>"
                + (f"<span style='color:#F59E0B'>Last-minute (+20%):</span> "
                   f"<span style='color:#F59E0B'>{fmt_cop(bd['last_minute_surcharge'])}</span><br>"
                   if bd['last_minute_applied'] else "")
                + f"<br><b style='color:#00FFD1;font-size:1.2em'>{fmt_cop(bd['total'])}</b> COP Total"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='sf-divider'>", unsafe_allow_html=True)

    # ── Step 4: Process ──
    st.markdown("### Paso 4 — Procesar")
    col_btn, col_note = st.columns([1, 3])
    with col_btn:
        process_btn = st.button("⚡ Procesar Cambio", use_container_width=True)
    with col_note:
        st.caption("El sistema validará, clasificará con IA, recalculará el precio y enviará notificaciones.")

    if process_btn:
        with st.spinner("Procesando a través del pipeline de IA…"):
            reservation_obj = Reservation.from_dict(res.copy())
            event = create_event(selected_id, api_event_type, payload)

            updated_res, result = process_event(event, reservation_obj)

            if result["success"]:
                st.session_state.reservations[selected_id] = updated_res.to_dict()
                event.status = "processed"
                st.session_state.events.append(event.to_dict())
                st.session_state.sim_result = result
            else:
                st.session_state.sim_result = result

        st.rerun()

    # ── Step 5: Results ──
    if st.session_state.sim_result:
        result = st.session_state.sim_result
        st.markdown("### Resultado del Pipeline")

        if not result["success"]:
            errors = result.get("errors", ["Error desconocido"])
            st.markdown(
                f'<div class="sf-result-error">'
                f"<b style='color:#EF4444'>Error al procesar</b><br>"
                + "".join(f"<br>• {e}" for e in errors)
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            # ── AI Classification ──
            cl = result["classification"]
            intent = cl.get("intent", "—")
            prio = cl.get("priority", "—")
            rec = cl.get("recommendation", "—")
            reasoning = cl.get("reasoning", "")
            risk = cl.get("risk_score", 0)
            mode = cl.get("mode", "openai")
            prio_color = PRIORITY_COLOR.get(prio, "#6B7A93")
            rec_color = RECOMMEND_COLOR.get(rec, "#6B7A93")

            st.markdown(
                f'<div class="sf-card-accent">'
                f"<b style='color:#00FFD1'>🤖 Clasificación IA</b>"
                + (f" <span style='color:#6B7A93;font-size:.75em'>[modo demo]</span>" if mode == "rules-based" else "")
                + f"<br><br>"
                f'<div class="ai-box">'
                f'<div class="ai-chip">Intent <span>{intent.upper()}</span></div>'
                f'<div class="ai-chip">Prioridad <span style="color:{prio_color}">{prio.upper()}</span></div>'
                f'<div class="ai-chip">Recomendación <span style="color:{rec_color}">{rec.upper()}</span></div>'
                f'<div class="ai-chip">Riesgo <span>{risk:.0%}</span></div>'
                f"</div>"
                + (f"<br><span style='color:#6B7A93;font-size:.85em;font-style:italic'>{reasoning}</span>" if reasoning else "")
                + "</div>",
                unsafe_allow_html=True,
            )

            # ── New price ──
            new_price = result.get("new_price", 0)
            bd = result.get("price_breakdown", {})
            col_price, col_break = st.columns([1, 2])
            with col_price:
                st.markdown(
                    f'<div class="sf-metric">'
                    f'<div class="sf-metric-value">{fmt_cop(new_price)}</div>'
                    f'<div class="sf-metric-label">Nuevo Precio Total</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_break:
                if bd:
                    st.markdown(
                        f'<div class="sf-card" style="height:100%">'
                        f"<b style='color:#FFFFFF'>Desglose</b><br><br>"
                        f"<span style='color:#6B7A93'>Noches:</span> {bd.get('nights', '—')}<br>"
                        f"<span style='color:#6B7A93'>Base:</span> {fmt_cop(bd.get('base_price', 0))} COP<br>"
                        f"<span style='color:#6B7A93'>Extra huéspedes:</span> {fmt_cop(bd.get('extra_guest_fee', 0))} COP<br>"
                        + (f"<span style='color:#F59E0B'>Last-minute:</span> {fmt_cop(bd.get('last_minute_surcharge', 0))} COP<br>" if bd.get('last_minute_applied') else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )

            # ── Messages ──
            st.markdown("<br>", unsafe_allow_html=True)
            col_gm, col_hm = st.columns(2)
            with col_gm:
                st.markdown("<b style='color:#FFFFFF'>Mensaje al Huésped</b>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="sf-message">{result.get("guest_message", "—")}</div>',
                    unsafe_allow_html=True,
                )
            with col_hm:
                st.markdown("<b style='color:#FFFFFF'>Mensaje al Anfitrión</b>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="sf-message-host">{result.get("host_message", "—")}</div>',
                    unsafe_allow_html=True,
                )

            # ── Notifications ──
            notif = result.get("notifications", {})
            email_r = notif.get("email", {})
            wa_r = notif.get("whatsapp", {})

            st.markdown("<br><b style='color:#FFFFFF'>Notificaciones Enviadas</b>", unsafe_allow_html=True)
            col_e, col_w = st.columns(2)
            with col_e:
                icon = "✅" if email_r.get("success") else "❌"
                sim = " (simulado)" if email_r.get("simulated") else ""
                st.markdown(
                    f'<div class="sf-card" style="padding:14px">'
                    f"{icon} <b>Email</b>{sim}<br>"
                    f"<span style='color:#6B7A93;font-size:.85em'>{email_r.get('message', email_r.get('to', ''))}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_w:
                icon = "✅" if wa_r.get("success") else "❌"
                sim = " (simulado)" if wa_r.get("simulated") else ""
                st.markdown(
                    f'<div class="sf-card" style="padding:14px">'
                    f"{icon} <b>WhatsApp</b>{sim}<br>"
                    f"<span style='color:#6B7A93;font-size:.85em'>{wa_r.get('message', wa_r.get('to', ''))}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Clear result button
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 Limpiar resultado"):
            st.session_state.sim_result = None
            st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_state()
    page = render_sidebar()

    if page == "Dashboard":
        page_dashboard()
    elif page == "Reservas":
        page_reservations()
    elif page == "Eventos":
        page_events()
    elif page == "Simulador de Cambios":
        page_simulator()


if __name__ == "__main__":
    main()
