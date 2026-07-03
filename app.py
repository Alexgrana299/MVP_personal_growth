import hashlib
import html
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client


APP_NAME = "Loom"
APP_DEFAULT_TIMEZONE = "America/Monterrey"

DAY_LETTERS = ["D", "L", "M", "X", "J", "V", "S"]
CATEGORIES = ["Mañana", "Tarde", "Noche", "Deseables"]
TRACKER_COL_WEIGHTS = [0.55, 2.8, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42]

SPANISH_DAYS = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

DAY_NAMES_SHORT = {
    "D": "Dom",
    "L": "Lun",
    "M": "Mar",
    "X": "Mié",
    "J": "Jue",
    "V": "Vie",
    "S": "Sáb",
}

SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def create_app_icon(size: int = 64) -> Image.Image:
    """Crea el favicon de Loom en memoria.

    Streamlit acepta un objeto PIL como page_icon, así evitamos depender de
    un archivo externo y el favicon queda alineado con el logo de la app.
    """
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Fondo con gradiente cyan, similar al logo del header.
    top = (14, 116, 144)
    mid = (6, 182, 212)
    bottom = (103, 232, 249)

    for y in range(size):
        if y < size / 2:
            ratio = y / (size / 2)
            start, end = top, mid
        else:
            ratio = (y - size / 2) / (size / 2)
            start, end = mid, bottom

        color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3))
        draw.line([(0, y), (size, y)], fill=color + (255,))

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((2, 2, size - 2, size - 2), radius=18, fill=255)
    img.putalpha(mask)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
    except Exception:
        font = ImageFont.load_default()

    text = "L"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1] - 1
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


APP_ICON = create_app_icon()


st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    header[data-testid="stHeader"] {
        display: none;
    }

    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }

    [data-testid="stDecoration"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
        color: #0f172a;
    }

    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1.25rem;
        max-width: 1500px;
    }

    .pg-title {
        font-size: 2.4rem;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 0.15rem;
        letter-spacing: -0.05em;
    }

    .pg-date {
        color: #475569;
        font-size: 1.02rem;
        font-weight: 700;
        padding-top: 0.45rem;
        margin-bottom: 1rem;
    }

    .pg-user {
        color: #0f172a;
        font-size: 1.02rem;
        font-weight: 800;
        text-align: right;
        margin-top: 0.25rem;
    }

    /* ---------- Login card ---------- */
    .login-card-title {
        text-align: center;
    }

    .login-card-subtitle {
        text-align: center;
        color: #475569;
        font-size: 0.98rem;
        font-weight: 600;
        margin-bottom: 1.4rem;
    }

    /* ---------- Panels / expanders ---------- */
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        background: #ffffff;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
        margin-bottom: 1rem;
    }

    div[data-testid="stExpander"] summary {
        font-weight: 900;
        color: #0f172a;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #cffafe;
        padding: 0.9rem 1rem;
        border-radius: 18px;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-weight: 800;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 900;
    }

    /* ---------- Tracker header (built with st.columns, same weights as rows) ---------- */
    .tr-head-label {
        font-weight: 900;
        color: #475569;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0.5rem 0.4rem;
    }

    .tr-head-day {
        text-align: center;
        font-weight: 900;
        color: #475569;
        font-size: 0.82rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.4rem 0.05rem;
        margin: 0;
        box-sizing: border-box;
        width: 100%;
    }

    .tr-head-day-current {
        text-align: center;
        font-weight: 900;
        color: #0891b2;
        background: #ecfeff;
        border: 1px solid #67e8f9;
        border-radius: 10px;
        padding: 0.4rem 0.05rem;
        margin: 0;
        box-sizing: border-box;
        width: 100%;
    }

    .tracker-section {
        margin-top: 0.6rem;
        margin-bottom: 0.35rem;
        padding: 0.5rem 0.85rem;
        background: #ecfeff;
        border: 1px solid #cffafe;
        border-left: 6px solid #06b6d4;
        border-radius: 14px;
        color: #0f172a;
        font-weight: 900;
        font-size: 0.92rem;
    }

    .habit-name {
        min-height: 2.15rem;
        display: flex;
        align-items: center;
        padding: 0.2rem 0.35rem;
        color: #0f172a;
        font-weight: 650;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.92rem;
    }

    /* ---------- Checkboxes ---------- */
    div[data-testid="stCheckbox"] {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 2.15rem;
        width: 100%;
        margin: 0;
        box-sizing: border-box;
    }

    div[data-testid="stCheckbox"] label {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        cursor: pointer;
    }

    div[data-testid="stCheckbox"] p {
        display: none;
    }

    /* Streamlit dibuja el checkbox con el <input> nativo invisible superpuesto
       a un recuadro propio (SVG/CSS). Si se le cambia el tamaño solo al
       input, ambos quedan desalineados y se ven como dos casillas encimadas.
       Por eso se escala la etiqueta completa (label), que contiene ambos
       elementos, para que crezcan juntos y en la misma proporción. */
    div[data-testid="stCheckbox"] label > span:first-child {
        transform: scale(1.05);
    }

    div[data-testid="stCheckbox"]:has(input:disabled) {
        opacity: 0.35;
    }

    div[data-testid="stCheckbox"]:has(input:disabled) label {
        cursor: not-allowed;
    }

    /* ---------- Excluded cell (habit doesn't apply that day) ---------- */
    .cell-excluded {
        min-height: 2.15rem;
        display: flex;
        justify-content: center;
        align-items: center;
        color: #cbd5e1;
        font-weight: 900;
        font-size: 0.95rem;
    }

    .stButton button {
        border-radius: 14px;
        font-weight: 800;
    }

    /* ---------- Apartados colapsables (Mañana / Tarde / Noche, etc.) ---------- */
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        margin-bottom: 0.6rem;
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        background: #f0fdfa;
        color: #0f172a;
        font-weight: 800;
        font-size: 0.95rem;
        padding: 0.6rem 1rem !important;
    }

    div[data-testid="stExpander"] summary:hover {
        background: #ecfeff;
    }

    div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        padding-top: 0.3rem;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #0e7490 0%, #06b6d4 50%, #67e8f9 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 16px !important;
        font-weight: 900 !important;
        height: 3rem !important;
        box-shadow: 0 12px 28px rgba(6, 182, 212, 0.32);
    }

    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #155e75 0%, #0891b2 50%, #22d3ee 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #0f172a;
    }

    /* ---------- Vista móvil (celular) ---------- */
    .st-key-view_switch_wrap {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 0.4rem;
    }

    .st-key-view_switch_wrap .stButton button {
        background: transparent !important;
        border: 1px solid #e2e8f0 !important;
        color: #475569 !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        height: 2.1rem !important;
        padding: 0 0.9rem !important;
        box-shadow: none !important;
    }

    .mv-section-title {
        font-weight: 900;
        color: #475569;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
    }

    .mv-selected-day {
        color: #0891b2;
        background: #ecfeff;
        border: 1px solid #cffafe;
        border-radius: 12px;
        padding: 0.5rem 0.75rem;
        font-weight: 800;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }

    .mv-habit-name {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.4rem;
        color: #0f172a;
        font-weight: 650;
        font-size: 0.95rem;
    }

    .mv-not-applicable {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #94a3b8;
        font-weight: 700;
        font-size: 0.7rem;
        text-align: center;
    }

    /* Cada fila hábito + checkbox se ve como una tarjeta individual: fondo
       blanco, esquinas redondeadas, buen espacio entre tarjetas. */
    .st-key-mobile_tracker div[data-testid="stHorizontalBlock"] {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        border-radius: 14px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.55rem;
        align-items: center;
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.03);
    }

    .st-key-mobile_tracker div[data-testid="stCheckbox"] {
        min-height: 2rem;
    }

    /* Checkbox grande y fácil de tocar con el pulgar (se escala completo). */
    .st-key-mobile_tracker div[data-testid="stCheckbox"] label > span:first-child {
        transform: scale(1.5);
    }

    /* Insignia de racha (⭐) en su propia columna angosta, en celular. */
    .mv-streak-cell {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 2rem;
        color: #b45309;
        font-weight: 900;
        font-size: 0.82rem;
        white-space: nowrap;
    }

    /* Insignia de racha en la tabla de escritorio. */
    .streak-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.2rem;
        min-height: 2.15rem;
        color: #b45309;
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 10px;
        font-weight: 900;
        font-size: 0.78rem;
    }

    .streak-badge-empty {
        min-height: 2.15rem;
    }

    /* Botones "pill" del selector de día (celular). El día seleccionado usa
       type="primary" (gradiente cyan); los demás quedan neutros. Se limita
       a este contenedor para no tocar los demás botones de la app. */
    .st-key-mobile_day_pills .stButton button {
        border-radius: 12px;
        padding: 0.4rem 0;
        font-size: 0.85rem;
    }

    /* ---------- Responsive behaviour ---------- */

    /* Tracker rows (habit name + 7 day checkboxes) never wrap, on any device.
       If they don't fit (small phones), the wrapper scrolls horizontally instead
       of breaking into a stacked, unreadable layout. */
    .st-key-tracker_scroll [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 100%;
    }

    .st-key-tracker_scroll {
        overflow-x: auto !important;
    }

    /* Filas de la vista móvil (resumen, racha/nombre/check, selector de día):
       por default Streamlit apila las columnas en pantallas angostas, lo que
       rompía el diseño en celular. Se fuerza a que siempre queden en fila. */
    .st-key-mobile_tracker [data-testid="stHorizontalBlock"],
    .st-key-mobile_day_pills [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 100%;
    }

    .st-key-mobile_tracker {
        overflow-x: auto !important;
    }

    .st-key-mobile_day_pills [data-testid="column"] {
        min-width: 0;
    }

    /* From 600px up (tablets and desktop) keep the chart/metrics column and the
       tracker column side by side, in a single view, instead of stacking. */
    @media (min-width: 600px) {
        .st-key-main_layout [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
        }
    }

    @media (max-width: 900px) {
        .pg-title {
            font-size: 2rem;
        }

        .pg-user {
            text-align: left;
            margin-bottom: 0.7rem;
        }

        .habit-name {
            font-size: 0.84rem;
        }
    }

    /* Phones only: below this point the app is allowed to stack and scroll. */
    @media (max-width: 599px) {
        .pg-title {
            font-size: 1.7rem;
        }

        .habit-name {
            font-size: 0.78rem;
            min-height: 1.9rem;
        }

        .tr-head-label,
        .tr-head-day,
        .tr-head-day-current {
            font-size: 0.7rem;
            padding: 0.32rem 0.05rem;
        }
    }


    /* ---------- Mobile responsive tracker: dropdown + 3-column habit rows ---------- */
    @media (max-width: 599px) {
        html, body, [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
            max-width: 100vw !important;
        }

        .block-container {
            max-width: 100vw !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }

        .st-key-mobile_summary,
        .st-key-mobile_summary *,
        .st-key-mobile_tracker,
        .st-key-mobile_tracker * {
            box-sizing: border-box;
        }

        .st-key-mobile_summary {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }

        .st-key-mobile_summary [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            max-width: 100% !important;
            gap: 0.65rem !important;
        }

        .st-key-mobile_summary [data-testid="column"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            flex: 1 1 100% !important;
        }

        .st-key-mobile_summary div[data-testid="stMetric"] {
            width: 100% !important;
            margin-bottom: 0 !important;
        }

        .mv-day-select-label,
        .mv-habit-label {
            display: block;
            margin: 0.25rem 0 0.45rem;
            color: #475569;
            font-size: 0.78rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .st-key-mobile_day_dropdown div[data-baseweb="select"] > div {
            min-height: 46px;
            border-radius: 14px;
            background: #f8fafc;
            border-color: #cbd5e1;
        }

        .st-key-mobile_day_dropdown [data-baseweb="select"] span,
        .st-key-mobile_day_dropdown [data-baseweb="select"] div {
            font-weight: 800;
        }

        .st-key-mobile_tracker {
            width: 100% !important;
            max-width: 100vw !important;
            overflow-x: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stExpander"] {
            width: 100% !important;
            margin-bottom: 0.75rem !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05) !important;
        }

        .st-key-mobile_tracker div[data-testid="stExpander"] summary {
            min-height: 58px !important;
            padding: 0 1rem !important;
            font-size: 1rem !important;
            font-weight: 750 !important;
        }

        .st-key-mobile_tracker div[data-testid="stHorizontalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            background: #ffffff;
            border: 1px solid #f1f5f9;
            border-radius: 14px;
            padding: 0.55rem 0.35rem 0.55rem 0.25rem;
            margin-bottom: 0.45rem;
            gap: 0.18rem !important;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.03);
        }

        .st-key-mobile_tracker div[data-testid="column"] {
            min-width: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        /* En móvil las columnas se compactan agresivamente:
           streak angosto | texto flexible | checkbox angosto. */
        .st-key-mobile_tracker div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            flex: 0 0 28px !important;
            width: 28px !important;
            max-width: 28px !important;
        }

        .st-key-mobile_tracker div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            flex: 1 1 auto !important;
            width: auto !important;
            max-width: none !important;
        }

        .st-key-mobile_tracker div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
            flex: 0 0 44px !important;
            width: 44px !important;
            max-width: 44px !important;
        }

        .mv-streak-cell {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 2.8rem;
            color: #b45309;
            font-weight: 900;
            font-size: 0.68rem;
            white-space: nowrap;
        }

        .mv-streak-badge {
            min-width: 1.85rem;
            min-height: 1.7rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0;
            border-radius: 9px;
            border: 1px solid #fde68a;
            background: #fffbeb;
            color: #b45309;
            font-size: 0.66rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .mv-habit-name {
            min-height: 2.8rem;
            display: flex;
            align-items: center;
            color: #0f172a;
            font-weight: 800;
            font-size: 0.92rem;
            line-height: 1.2;
            overflow-wrap: anywhere;
            word-break: normal;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] {
            min-height: 2.8rem;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            min-height: 2.8rem;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            width: auto !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > span:first-child {
            transform: scale(1.55);
        }

        .mv-not-applicable {
            min-height: 2.8rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94a3b8;
            font-weight: 800;
            font-size: 0.68rem;
            text-align: center;
            line-height: 1.05;
        }
    }


    /* ---------- Mobile v4: no columns inside habit cards ---------- */
    @media (max-width: 599px) {
        .st-key-mobile_tracker {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }

        /* Neutraliza cualquier fila horizontal heredada dentro del tracker móvil. */
        .st-key-mobile_tracker [data-testid="stHorizontalBlock"] {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            overflow-x: hidden !important;
        }

        /* Ahora cada checkbox ES la card. Sin st.columns, no hay colapso lateral. */
        .st-key-mobile_tracker div[data-testid="stCheckbox"] {
            width: 100% !important;
            max-width: 100% !important;
            min-height: 58px !important;
            display: flex !important;
            align-items: center !important;
            background: #ffffff !important;
            border: 1px solid #f1f5f9 !important;
            border-radius: 14px !important;
            padding: 0.55rem 0.55rem 0.55rem 0.65rem !important;
            margin: 0 0 0.55rem 0 !important;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.03) !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            width: 100% !important;
            max-width: 100% !important;
            min-height: 44px !important;
            display: flex !important;
            flex-direction: row-reverse !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 0.75rem !important;
            cursor: pointer !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] p {
            display: block !important;
            margin: 0 !important;
            color: #0f172a !important;
            font-size: 0.95rem !important;
            font-weight: 850 !important;
            line-height: 1.18 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: normal !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > span:first-child {
            flex: 0 0 34px !important;
            width: 34px !important;
            max-width: 34px !important;
            transform: scale(1.45) !important;
            margin: 0 !important;
        }

        .mv-static-habit-row {
            width: 100%;
            min-height: 58px;
            display: grid;
            grid-template-columns: 34px minmax(0, 1fr) 52px;
            align-items: center;
            column-gap: 0.35rem;
            background: #ffffff;
            border: 1px solid #f1f5f9;
            border-radius: 14px;
            padding: 0.55rem 0.55rem 0.55rem 0.65rem;
            margin-bottom: 0.55rem;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.03);
            box-sizing: border-box;
            overflow: hidden;
        }

        .mv-row-streak {
            color: #b45309;
            font-size: 0.72rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .mv-row-streak-empty {
            visibility: hidden;
        }

        .mv-static-habit-name {
            min-width: 0;
            color: #0f172a;
            font-size: 0.95rem;
            font-weight: 850;
            line-height: 1.18;
            overflow-wrap: anywhere;
        }

        .mv-static-na {
            color: #94a3b8;
            font-size: 0.64rem;
            font-weight: 850;
            text-align: right;
            line-height: 1.05;
        }
    }


    /* ---------- Mobile v5: aesthetic full-width habit cards ---------- */
    @media (max-width: 599px) {
        .st-key-mobile_tracker div[data-testid="stExpanderDetails"] {
            padding: 0.65rem 0.65rem 0.75rem !important;
        }

        .st-key-mobile_tracker [data-testid="stVerticalBlock"],
        .st-key-mobile_tracker [data-testid="stVerticalBlock"] > div,
        .st-key-mobile_tracker [data-testid="stElementContainer"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_tracker [data-testid="stElementContainer"]:has(div[data-testid="stCheckbox"]) {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 0 0.6rem 0 !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            min-height: 60px !important;
            background: #ffffff !important;
            border: 1px solid #eaf0f6 !important;
            border-radius: 16px !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035) !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            width: 100% !important;
            max-width: 100% !important;
            min-height: 60px !important;
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) 42px !important;
            align-items: center !important;
            gap: 0.55rem !important;
            padding: 0.72rem 0.68rem 0.72rem 0.9rem !important;
            margin: 0 !important;
            cursor: pointer !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] p {
            display: block !important;
            min-width: 0 !important;
            max-width: 100% !important;
            margin: 0 !important;
            color: #0f172a !important;
            font-size: 0.98rem !important;
            font-weight: 850 !important;
            line-height: 1.18 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > span:first-child {
            justify-self: end !important;
            align-self: center !important;
            width: 28px !important;
            min-width: 28px !important;
            max-width: 28px !important;
            height: 28px !important;
            transform: scale(1.28) !important;
            transform-origin: center !important;
            margin: 0 !important;
        }

        .mv-static-habit-row {
            width: 100% !important;
            min-height: 60px !important;
            grid-template-columns: minmax(0, 1fr) 58px !important;
            column-gap: 0.55rem !important;
            border-color: #eaf0f6 !important;
            border-radius: 16px !important;
            padding: 0.72rem 0.68rem 0.72rem 0.9rem !important;
            margin-bottom: 0.6rem !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035) !important;
        }

        .mv-static-habit-name {
            font-size: 0.98rem !important;
            font-weight: 850 !important;
        }

        .mv-row-streak {
            display: inline-flex !important;
            margin-right: 0.28rem !important;
            color: #b45309 !important;
            font-size: 0.82rem !important;
            font-weight: 900 !important;
        }

        .mv-static-na {
            justify-self: end !important;
            color: #94a3b8 !important;
            font-size: 0.68rem !important;
            font-weight: 850 !important;
        }
    }


    /* ---------- Mobile v6: fix checkbox label grid order ---------- */
    @media (max-width: 599px) {
        .st-key-mobile_tracker {
            overflow-x: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stExpanderDetails"] {
            padding: 0.65rem 0.65rem 0.75rem !important;
        }

        .st-key-mobile_tracker [data-testid="stElementContainer"]:has(div[data-testid="stCheckbox"]) {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            display: block !important;
            margin: 0 0 0.62rem 0 !important;
            overflow: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            min-height: 62px !important;
            display: block !important;
            background: #ffffff !important;
            border: 1px solid #eaf0f6 !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035) !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            min-height: 62px !important;
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) 34px !important;
            grid-template-rows: auto !important;
            align-items: center !important;
            column-gap: 0.7rem !important;
            padding: 0.72rem 0.72rem 0.72rem 0.95rem !important;
            margin: 0 !important;
            box-sizing: border-box !important;
            cursor: pointer !important;
            overflow: hidden !important;
        }

        /* Streamlit pone primero el span del checkbox y después el contenedor del texto.
           Si no se reubican explícitamente, el texto cae en la columna angosta derecha. */
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > span:first-child {
            grid-column: 2 !important;
            grid-row: 1 !important;
            justify-self: end !important;
            align-self: center !important;
            width: 28px !important;
            min-width: 28px !important;
            max-width: 28px !important;
            height: 28px !important;
            transform: scale(1.28) !important;
            transform-origin: center !important;
            margin: 0 !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > div {
            grid-column: 1 !important;
            grid-row: 1 !important;
            min-width: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
            overflow: hidden !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > div p,
        .st-key-mobile_tracker div[data-testid="stCheckbox"] p {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            margin: 0 !important;
            color: #0f172a !important;
            font-size: 0.98rem !important;
            font-weight: 850 !important;
            line-height: 1.18 !important;
            white-space: normal !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            overflow-wrap: break-word !important;
            word-break: normal !important;
        }

        .mv-static-habit-row {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            min-height: 62px !important;
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) 58px !important;
            align-items: center !important;
            column-gap: 0.7rem !important;
            background: #ffffff !important;
            border: 1px solid #eaf0f6 !important;
            border-radius: 16px !important;
            padding: 0.72rem 0.72rem 0.72rem 0.95rem !important;
            margin: 0 0 0.62rem 0 !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035) !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .mv-static-habit-name {
            min-width: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
            color: #0f172a !important;
            font-size: 0.98rem !important;
            font-weight: 850 !important;
            line-height: 1.18 !important;
            overflow-wrap: break-word !important;
        }

        .mv-row-streak {
            display: inline-flex !important;
            margin-right: 0.28rem !important;
            color: #b45309 !important;
            font-size: 0.82rem !important;
            font-weight: 900 !important;
            white-space: nowrap !important;
        }

        .mv-static-na {
            justify-self: end !important;
            color: #94a3b8 !important;
            font-size: 0.68rem !important;
            font-weight: 850 !important;
            text-align: right !important;
        }
    }



    /* ---------- Mobile v7: visual streak column + aligned habit text ---------- */
    @media (max-width: 599px) {
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            grid-template-columns: minmax(0, 1fr) 34px !important;
        }

        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > div p,
        .st-key-mobile_tracker div[data-testid="stCheckbox"] p {
            font-variant-numeric: tabular-nums !important;
            letter-spacing: -0.01em !important;
        }

        .mv-static-habit-row {
            grid-template-columns: 2.65rem minmax(0, 1fr) 58px !important;
            column-gap: 0.45rem !important;
        }

        .mv-static-habit-name {
            grid-column: 2 !important;
        }

        .mv-row-streak {
            grid-column: 1 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 2.35rem !important;
            margin-right: 0 !important;
            color: #b45309 !important;
            font-size: 0.78rem !important;
            font-weight: 900 !important;
            white-space: nowrap !important;
        }

        .mv-static-na {
            grid-column: 3 !important;
        }
    }


    /* ---------- Mobile v8: hanging indent for streak + centered clean chart ---------- */
    @media (max-width: 599px) {
        /* El texto del checkbox móvil incluye un prefijo visual de streak.
           Con hanging-indent, si el hábito se parte en dos líneas, la segunda
           línea inicia donde inicia el texto del hábito, no debajo del streak. */
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label > div p,
        .st-key-mobile_tracker div[data-testid="stCheckbox"] p {
            padding-left: 2.75rem !important;
            text-indent: -2.75rem !important;
            overflow-wrap: break-word !important;
            word-break: normal !important;
        }

        /* Reserva visual de la columna streak también para filas no aplicables. */
        .mv-static-habit-row {
            grid-template-columns: 2.75rem minmax(0, 1fr) 58px !important;
        }

        .mv-row-streak {
            width: 2.45rem !important;
            min-width: 2.45rem !important;
            max-width: 2.45rem !important;
            justify-content: center !important;
        }

        .mv-static-habit-name {
            overflow-wrap: break-word !important;
            word-break: normal !important;
        }

        /* Plotly en móvil: ocupa todo el ancho disponible, sin desbordar y sin
           quedar visualmente cargado a la izquierda. */
        .st-key-mobile_chart,
        .st-key-mobile_chart [data-testid="stElementContainer"],
        .st-key-mobile_chart div[data-testid="stPlotlyChart"],
        .st-key-mobile_chart .js-plotly-plot,
        .st-key-mobile_chart .plot-container,
        .st-key-mobile_chart .svg-container {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            margin-left: auto !important;
            margin-right: auto !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_chart .modebar {
            display: none !important;
        }
    }


    /* ---------- Previous week summary card ---------- */
    .week-summary-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8feff 100%);
        border: 1px solid #cffafe;
        border-radius: 20px;
        padding: 1rem 1.1rem;
        margin: 0.25rem 0 1rem 0;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    }

    .week-summary-kicker {
        color: #475569;
        font-size: 0.78rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.35rem;
    }

    .week-summary-main {
        display: flex;
        align-items: baseline;
        gap: 0.65rem;
        margin-bottom: 0.35rem;
    }

    .week-summary-percent {
        color: #0f172a;
        font-size: 2.15rem;
        font-weight: 950;
        letter-spacing: -0.04em;
        line-height: 1;
    }

    .week-summary-sub {
        color: #64748b;
        font-size: 0.92rem;
        font-weight: 750;
    }

    .week-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.5rem;
        margin-top: 0.75rem;
    }

    .week-summary-chip {
        background: #ecfeff;
        border: 1px solid #cffafe;
        border-radius: 14px;
        padding: 0.55rem 0.65rem;
        color: #0f172a;
        font-size: 0.82rem;
        font-weight: 800;
        min-width: 0;
    }

    .week-summary-chip span {
        display: block;
        color: #64748b;
        font-size: 0.68rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.15rem;
    }

    @media (max-width: 599px) {
        .week-summary-card {
            padding: 0.95rem 0.9rem;
            border-radius: 18px;
        }

        .week-summary-grid {
            grid-template-columns: 1fr;
        }

        .week-summary-percent {
            font-size: 2rem;
        }
    }



    /* ---------- Mobile v11: final polish ---------- */
    @media (max-width: 599px) {
        /* Gana espacio real en iPhone sin provocar overflow. */
        .block-container {
            padding-left: 0.55rem !important;
            padding-right: 0.55rem !important;
        }

        /* El contenedor del tracker y sus expanders ocupan todo el ancho útil. */
        .st-key-mobile_tracker,
        .st-key-mobile_tracker > div,
        .st-key-mobile_tracker div[data-testid="stExpander"],
        .st-key-mobile_tracker div[data-testid="stExpanderDetails"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
        }

        .st-key-mobile_tracker div[data-testid="stExpanderDetails"] {
            padding-left: 0.38rem !important;
            padding-right: 0.38rem !important;
        }

        /* Cada card de hábito se estira al ancho completo del apartado. */
        .st-key-mobile_tracker [data-testid="stElementContainer"]:has(div[data-testid="stCheckbox"]),
        .st-key-mobile_tracker div[data-testid="stCheckbox"],
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label,
        .mv-static-habit-row {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
        }

        .st-key-mobile_tracker [data-testid="stElementContainer"]:has(div[data-testid="stCheckbox"]) {
            margin-left: 0 !important;
            margin-right: 0 !important;
        }

        /* Compacta ligeramente la card para que se sienta más full-width y menos flotante. */
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label {
            padding-left: 0.78rem !important;
            padding-right: 0.62rem !important;
        }

        .mv-static-habit-row {
            padding-left: 0.78rem !important;
            padding-right: 0.62rem !important;
        }

        /* Oculta por completo la leyenda azul redundante si quedó en caché/DOM. */
        .mv-selected-day {
            display: none !important;
        }

        /* Botón Guardar semana móvil: texto blanco y glow menos intenso. */
        .st-key-mobile_save_btn button {
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(6, 182, 212, 0.20) !important;
        }

        .st-key-mobile_save_btn button:hover {
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(6, 182, 212, 0.24) !important;
        }
    }


    /* ---------- Mobile v12: centered metrics + white primary button text ---------- */
    /* Streamlit suele pintar el texto del botón dentro de <p>/<span>; si no se
       fuerza también ahí, puede verse gris aunque el button tenga color blanco. */
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span {
        color: #ffffff !important;
    }

    @media (max-width: 599px) {
        /* Centra visualmente las tarjetas de métricas y elimina el sesgo lateral
           que Streamlit deja por el layout de columnas. */
        .st-key-mobile_summary {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            overflow-x: hidden !important;
        }

        .st-key-mobile_summary [data-testid="stHorizontalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            gap: 0.65rem !important;
        }

        .st-key-mobile_summary [data-testid="column"],
        .st-key-mobile_summary [data-testid="stElementContainer"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        .st-key-mobile_summary div[data-testid="stMetric"] {
            width: min(100%, 430px) !important;
            max-width: 430px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            box-sizing: border-box !important;
        }

        /* Botón móvil: blanco real en todos los nodos internos y glow discreto. */
        .st-key-mobile_save_btn button,
        .st-key-mobile_save_btn button *,
        .st-key-mobile_save_btn button p,
        .st-key-mobile_save_btn button span {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .st-key-mobile_save_btn button {
            box-shadow: 0 7px 16px rgba(6, 182, 212, 0.18) !important;
        }

        .st-key-mobile_save_btn button:hover {
            box-shadow: 0 8px 18px rgba(6, 182, 212, 0.22) !important;
        }
    }


    /* ---------- Loom branding ---------- */
    .pg-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }

    .pg-brand-login {
        justify-content: center;
        margin-bottom: 0.25rem;
    }

    .pg-brand-header {
        margin-bottom: 0.15rem;
    }

    .pg-brand .pg-title {
        margin: 0;
        line-height: 1;
    }

    .pg-logo-mark {
        width: 44px;
        height: 44px;
        border-radius: 15px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 auto;
        color: #ffffff;
        font-size: 1.15rem;
        font-weight: 950;
        letter-spacing: -0.08em;
        background: linear-gradient(135deg, #0e7490 0%, #06b6d4 55%, #67e8f9 100%);
        box-shadow: 0 12px 26px rgba(6, 182, 212, 0.22);
        border: 1px solid rgba(255, 255, 255, 0.55);
    }

    .pg-brand-header .pg-logo-mark {
        box-shadow: none !important;
    }

    /* ---------- Mobile metric cards without Streamlit column constraints ---------- */
    .mobile-metrics-stack {
        width: 100%;
        max-width: 100%;
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.7rem;
        margin: 0 auto;
        box-sizing: border-box;
    }

    .mobile-metric-card {
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid #cffafe;
        border-radius: 18px;
        padding: 0.95rem 1rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.055);
    }

    .mobile-metric-label {
        color: #64748b;
        font-size: 0.83rem;
        line-height: 1.1;
        font-weight: 850;
        margin-bottom: 0.28rem;
    }

    .mobile-metric-value {
        color: #0f172a;
        font-size: 2rem;
        line-height: 1;
        font-weight: 950;
        letter-spacing: -0.04em;
    }

    @media (min-width: 600px) {
        .mobile-metrics-stack {
            max-width: 430px;
        }
    }

    @media (max-width: 599px) {
        .pg-brand-header .pg-logo-mark {
            width: 38px;
            height: 38px;
            border-radius: 13px;
            font-size: 1rem;
        }

        .pg-brand-login .pg-logo-mark {
            width: 42px;
            height: 42px;
        }

        .pg-brand-header {
            gap: 0.55rem;
        }

        .mobile-metrics-stack {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        .mobile-metric-card {
            width: 100% !important;
            max-width: 100% !important;
        }
    }


    /* ---------- Mobile v10: final login/header/chart/card polish ---------- */
    .pg-brand-login {
        margin-bottom: 0.95rem !important;
    }

    .pg-brand-login .pg-logo-mark {
        box-shadow: 0 6px 14px rgba(6, 182, 212, 0.10) !important;
    }

    @media (max-width: 599px) {
        .pg-brand-login {
            margin-bottom: 1.05rem !important;
        }

        .pg-brand-login .pg-logo-mark {
            box-shadow: 0 5px 12px rgba(6, 182, 212, 0.08) !important;
        }

        /* El tracker móvil no debe tener scroll propio ni horizontal.
           La única navegación debe ser el scroll vertical normal de la página. */
        .st-key-mobile_tracker,
        .st-key-mobile_tracker > div,
        .st-key-mobile_tracker div[data-testid="stExpander"],
        .st-key-mobile_tracker div[data-testid="stExpanderDetails"],
        .st-key-mobile_tracker [data-testid="stVerticalBlock"],
        .st-key-mobile_tracker [data-testid="stElementContainer"],
        .st-key-mobile_tracker div[data-testid="stCheckbox"],
        .st-key-mobile_tracker div[data-testid="stCheckbox"] label,
        .mv-static-habit-row {
            overflow-x: hidden !important;
            max-width: 100% !important;
            overscroll-behavior-x: none !important;
            touch-action: pan-y !important;
        }

        .st-key-mobile_tracker {
            overflow-y: visible !important;
        }

        .st-key-mobile_tracker div[data-testid="stExpanderDetails"],
        .st-key-mobile_tracker [data-testid="stVerticalBlock"] {
            overflow-y: visible !important;
        }

        /* La gráfica móvil solo conserva eje X. */
        .st-key-mobile_chart .yaxislayer-above,
        .st-key-mobile_chart .yaxislayer-below,
        .st-key-mobile_chart .ytick,
        .st-key-mobile_chart .ygrid,
        .st-key-mobile_chart .yzl,
        .st-key-mobile_chart .ytitle {
            display: none !important;
        }
    }


    /* ---------- v11: favicon-aligned branding + global clean chart ---------- */
    .pg-brand-login .pg-logo-mark {
        box-shadow: 0 4px 10px rgba(6, 182, 212, 0.06) !important;
    }

    .pg-brand-login {
        margin-bottom: 1.18rem !important;
    }

    .login-card-subtitle {
        margin-top: 0.35rem !important;
    }

    /* Para escritorio y móvil: la gráfica conserva solo el eje X.
       El eje Y queda oculto desde Plotly, pero esto cubre cualquier capa
       residual que Streamlit/Plotly deje en el DOM. */
    div[data-testid="stPlotlyChart"] .yaxislayer-above,
    div[data-testid="stPlotlyChart"] .yaxislayer-below,
    div[data-testid="stPlotlyChart"] .ytick,
    div[data-testid="stPlotlyChart"] .ygrid,
    div[data-testid="stPlotlyChart"] .yzl,
    div[data-testid="stPlotlyChart"] .ytitle {
        display: none !important;
    }


    /* ---------- v12: metric cards without internal scroll ---------- */
    .mobile-summary-shell {
        width: 100%;
        max-width: 100%;
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
        box-sizing: border-box;
    }

    @media (max-width: 599px) {
        .mobile-summary-shell,
        .mobile-summary-shell *,
        .mobile-metrics-stack,
        .mobile-metric-card {
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
            overflow-y: visible !important;
            box-sizing: border-box !important;
        }

        .mobile-summary-shell {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .mobile-metrics-stack {
            display: grid !important;
            grid-template-columns: 1fr !important;
            gap: 0.7rem !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        .mobile-metric-card {
            position: static !important;
            flex: none !important;
            width: 100% !important;
            max-width: 100% !important;
        }
    }


    /* ---------- Product retention layer: today hero, autosave and heatmap ---------- */
    .today-hero {
        background: linear-gradient(135deg, #ecfeff 0%, #ffffff 58%, #f8fafc 100%);
        border: 1px solid #cffafe;
        border-radius: 24px;
        padding: 1.05rem 1.1rem;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
        margin-bottom: 1rem;
    }

    .today-hero-kicker {
        color: #0891b2;
        font-size: 0.78rem;
        font-weight: 950;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.25rem;
    }

    .today-hero-main {
        color: #0f172a;
        font-size: 2.15rem;
        line-height: 1;
        font-weight: 950;
        letter-spacing: -0.05em;
    }

    .today-hero-status {
        color: #0f172a;
        font-size: 1rem;
        font-weight: 900;
        margin-top: 0.35rem;
    }

    .today-progress-track {
        width: 100%;
        height: 12px;
        background: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 0.75rem;
    }

    .today-progress-fill {
        height: 100%;
        background: linear-gradient(135deg, #0e7490 0%, #06b6d4 65%, #67e8f9 100%);
        border-radius: 999px;
        transition: width 220ms ease;
    }

    .today-hero-message {
        color: #475569;
        font-size: 0.88rem;
        font-weight: 750;
        margin-top: 0.65rem;
    }

    .autosave-note {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        color: #0f766e;
        background: #f0fdfa;
        border: 1px solid #ccfbf1;
        border-radius: 999px;
        padding: 0.38rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 850;
        margin: 0.15rem 0 0.85rem 0;
    }

    .selected-day-banner {
        color: #334155;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 0.6rem 0.75rem;
        font-size: 0.83rem;
        font-weight: 850;
        margin: 0.5rem 0 0.75rem 0;
    }

    .insight-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 0.9rem 1rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045);
        margin-bottom: 1rem;
    }

    .insight-card-title {
        color: #0f172a;
        font-size: 0.92rem;
        font-weight: 950;
        margin-bottom: 0.15rem;
    }

    .insight-card-subtitle {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 750;
        margin-bottom: 0.45rem;
    }

    .settings-spacer {
        height: 0.75rem;
    }

    @media (max-width: 599px) {
        .today-hero {
            padding: 0.95rem 0.9rem;
            border-radius: 20px;
            margin-bottom: 0.85rem;
        }

        .today-hero-main {
            font-size: 2rem;
        }

        .today-progress-track {
            height: 11px;
        }

        .autosave-note {
            width: 100%;
            justify-content: center;
            box-sizing: border-box;
        }

        .insight-card {
            border-radius: 18px;
            padding: 0.85rem 0.75rem;
        }
    }


</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def inject_browser_timezone_script() -> None:
    """Detecta la zona horaria del navegador y la guarda en la URL.

    Streamlit corre en servidor; `date.today()` usa la fecha del servidor,
    no la del usuario. Este script obtiene la zona horaria real del navegador
    con JavaScript y la manda a Python mediante query params. Si cambia, recarga
    una vez la página para que toda la app use la fecha local correcta.
    """
    components.html(
        """
        <script>
        (function () {
            try {
                const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                if (!tz) return;

                const currentUrl = new URL(window.parent.location.href);
                const currentTz = currentUrl.searchParams.get("tz");

                if (currentTz !== tz) {
                    currentUrl.searchParams.set("tz", tz);
                    window.parent.history.replaceState(null, "", currentUrl.toString());
                    window.parent.location.reload();
                }
            } catch (error) {
                console.warn("No se pudo detectar la zona horaria del navegador:", error);
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def get_query_param(name: str) -> str | None:
    """Lee query params compatible con versiones recientes y antiguas de Streamlit."""
    try:
        value = st.query_params.get(name, None)
    except Exception:
        try:
            params = st.experimental_get_query_params()
            value = params.get(name, [None])
        except Exception:
            value = None

    if isinstance(value, list):
        return value[0] if value else None

    return value


def get_user_timezone_name() -> str:
    tz_name = get_query_param("tz")

    if not tz_name:
        return APP_DEFAULT_TIMEZONE

    try:
        ZoneInfo(tz_name)
        return tz_name
    except ZoneInfoNotFoundError:
        return APP_DEFAULT_TIMEZONE


def get_local_today() -> date:
    """Fecha local del usuario, no del servidor."""
    return datetime.now(ZoneInfo(get_user_timezone_name())).date()


inject_browser_timezone_script()


@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def format_spanish_date(target_date: date) -> str:
    day_name = SPANISH_DAYS[target_date.weekday()]
    month_name = SPANISH_MONTHS[target_date.month]
    return f"{day_name.capitalize()} {target_date.day} de {month_name} de {target_date.year}"


def login():
    col_left, col_center, col_right = st.columns([1, 1.2, 1])

    with col_center:
        st.markdown(
            f"""
            <div class='pg-brand pg-brand-login'>
                <div class='pg-logo-mark' aria-hidden='true'>L</div>
                <div class='pg-title login-card-title'>{APP_NAME}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='login-card-subtitle'>Tu sistema personal de hábitos, "
            "progreso y consistencia.</div>",
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button(
                "Iniciar sesión", use_container_width=True, type="primary"
            )

        if submitted:
            users = dict(st.secrets["users"])

            if username in users and hash_password(password) == users[username]:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["display_name"] = st.secrets["user_names"].get(
                    username, username
                )
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")


def get_week_start(today: date) -> date:
    days_since_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_since_sunday)


def get_day_letter(target_date: date) -> str:
    mapping = {
        6: "D",
        0: "L",
        1: "M",
        2: "X",
        3: "J",
        4: "V",
        5: "S",
    }
    return mapping[target_date.weekday()]


def load_habits(username: str) -> pd.DataFrame:
    supabase = get_supabase_client()

    response = (
        supabase
        .table("habits")
        .select("*")
        .eq("user_name", username)
        .eq("active", True)
        .order("sort_order")
        .execute()
    )

    df = pd.DataFrame(response.data)

    if df.empty:
        return df

    df["category"] = pd.Categorical(df["category"], categories=CATEGORIES, ordered=True)

    # sort_order puede venir como texto desde Supabase; se fuerza a numérico
    # para que el orden de inserción (1, 2, 3, ...) nunca se interprete como
    # texto (donde "10" quedaría antes que "2").
    df["sort_order"] = pd.to_numeric(df["sort_order"], errors="coerce").fillna(0)

    # Orden real: categoría + sort_order.
    # Si por datos antiguos hay sort_order duplicado o nulo, se usa created_at/id
    # solo como desempate estable. Nunca se ordena alfabéticamente por hábito.
    if "created_at" in df.columns:
        df["_created_sort"] = pd.to_datetime(df["created_at"], errors="coerce")
    else:
        df["_created_sort"] = pd.NaT

    if "id" not in df.columns:
        df["id"] = ""

    df = (
        df.sort_values(["category", "sort_order", "_created_sort", "id"], kind="stable")
        .drop(columns=["_created_sort"], errors="ignore")
        .reset_index(drop=True)
    )

    return df


def load_week_logs(username: str, week_start: date, week_end: date) -> pd.DataFrame:
    supabase = get_supabase_client()

    response = (
        supabase
        .table("habit_logs")
        .select("*")
        .eq("user_name", username)
        .gte("fecha", week_start.isoformat())
        .lte("fecha", week_end.isoformat())
        .execute()
    )

    return pd.DataFrame(response.data)


def load_all_logs(username: str) -> pd.DataFrame:
    supabase = get_supabase_client()

    response = (
        supabase
        .table("habit_logs")
        .select("*")
        .eq("user_name", username)
        .order("fecha")
        .limit(50000)
        .execute()
    )

    return pd.DataFrame(response.data)


def get_next_sort_order(username: str, category: str) -> int:
    """Siguiente posición al final del apartado.

    Se calcula en Python para evitar errores si sort_order quedó guardado
    como texto o si hay datos antiguos con valores raros.
    """
    supabase = get_supabase_client()

    order_response = (
        supabase
        .table("habits")
        .select("sort_order")
        .eq("user_name", username)
        .eq("category", category)
        .execute()
    )

    existing_orders = []
    for row in order_response.data:
        raw_value = row.get("sort_order")
        if raw_value is None:
            continue
        try:
            existing_orders.append(int(raw_value))
        except (TypeError, ValueError):
            continue

    return (max(existing_orders) + 1) if existing_orders else 1


def add_habit(username: str, category: str, habit_name: str, active_days: list[str] | None = None):
    supabase = get_supabase_client()
    habit_name = habit_name.strip()
    active_days = active_days or list(DAY_LETTERS)

    existing = (
        supabase
        .table("habits")
        .select("id, active")
        .eq("user_name", username)
        .eq("category", category)
        .eq("habit_name", habit_name)
        .execute()
    )

    next_order = get_next_sort_order(username, category)

    if existing.data:
        update_payload = {
            "active": True,
            "active_days": active_days,
            "sort_order": next_order,
        }

        # Si el hábito ya existía (activo o eliminado), al volverlo a agregar
        # desde el formulario se manda al final del apartado. Esto corrige casos
        # como "Beber agua" reapareciendo en medio por conservar un sort_order viejo.
        supabase.table("habits").update(update_payload).eq("id", existing.data[0]["id"]).execute()
        return

    supabase.table("habits").insert({
        "user_name": username,
        "category": category,
        "habit_name": habit_name,
        "sort_order": next_order,
        "active": True,
        "active_days": active_days,
    }).execute()


def deactivate_habit(habit_id: str):
    supabase = get_supabase_client()
    supabase.table("habits").update({"active": False}).eq("id", habit_id).execute()


def update_habit_active_days(habit_id: str, active_days: list[str]):
    supabase = get_supabase_client()
    supabase.table("habits").update({"active_days": active_days}).eq("id", habit_id).execute()


def sync_habit_logs_metadata(username: str, habit_id: str, habit_name: str | None = None, category: str | None = None):
    """Mantiene habit_logs alineado con la identidad visible del hábito.

    La relación real vive en habit_id. Aun así, habit_logs guarda habit_name y
    category como snapshot para reportes/descargas; si no se actualizan, Excel
    y resúmenes pueden mostrar nombres viejos aunque la racha siga bien.
    """
    payload = {}

    if habit_name is not None:
        payload["habit_name"] = habit_name

    if category is not None:
        payload["category"] = category

    if not payload:
        return

    supabase = get_supabase_client()
    (
        supabase
        .table("habit_logs")
        .update(payload)
        .eq("user_name", username)
        .eq("habit_id", habit_id)
        .execute()
    )


def normalize_habit_orders(username: str) -> None:
    """Reescribe sort_order como 1..N dentro de cada apartado.

    Esto evita huecos, duplicados y rarezas después de mover hábitos entre
    apartados o recuperar hábitos eliminados.
    """
    supabase = get_supabase_client()
    habits_df = load_habits(username)

    if habits_df.empty:
        return

    for category in CATEGORIES:
        category_habits = habits_df[habits_df["category"] == category].copy()
        if category_habits.empty:
            continue

        category_habits = category_habits.sort_values(["sort_order", "id"], kind="stable")

        for order, (_, habit) in enumerate(category_habits.iterrows(), start=1):
            current_order = int(habit.get("sort_order", 0) or 0)
            if current_order == order:
                continue

            (
                supabase
                .table("habits")
                .update({"sort_order": order})
                .eq("id", habit["id"])
                .execute()
            )


def update_habit_details(
    username: str,
    habit_id: str,
    habit_name: str,
    category: str,
    active_days: list[str],
) -> None:
    """Actualiza nombre, apartado y días sin cambiar el habit_id.

    Ese punto es clave: no se crea un hábito nuevo. Se conserva el mismo ID,
    por lo tanto las rachas y el histórico siguen conectados.
    """
    supabase = get_supabase_client()
    habit_name = habit_name.strip()

    current_response = (
        supabase
        .table("habits")
        .select("category, sort_order")
        .eq("id", habit_id)
        .eq("user_name", username)
        .limit(1)
        .execute()
    )

    current_row = current_response.data[0] if current_response.data else {}
    current_category = current_row.get("category")

    update_payload = {
        "habit_name": habit_name,
        "category": category,
        "active_days": active_days,
    }

    # Si el usuario cambia el apartado desde el selector, se manda al final del
    # nuevo apartado. Para ajustar una posición exacta usa Subir/Bajar después.
    if current_category != category:
        update_payload["sort_order"] = get_next_sort_order(username, category)

    (
        supabase
        .table("habits")
        .update(update_payload)
        .eq("id", habit_id)
        .eq("user_name", username)
        .execute()
    )

    sync_habit_logs_metadata(
        username=username,
        habit_id=habit_id,
        habit_name=habit_name,
        category=category,
    )
    normalize_habit_orders(username)


def swap_habit_sort_orders(first_habit: pd.Series, second_habit: pd.Series) -> None:
    supabase = get_supabase_client()

    first_order = int(first_habit.get("sort_order", 0) or 0)
    second_order = int(second_habit.get("sort_order", 0) or 0)

    (
        supabase
        .table("habits")
        .update({"sort_order": second_order})
        .eq("id", first_habit["id"])
        .execute()
    )
    (
        supabase
        .table("habits")
        .update({"sort_order": first_order})
        .eq("id", second_habit["id"])
        .execute()
    )


def move_habit(username: str, habit_id: str, direction: str) -> tuple[bool, str]:
    """Mueve un hábito una posición visible hacia arriba o hacia abajo.

    - Dentro del mismo apartado intercambia sort_order con el vecino.
    - Si está en el borde, lo mueve al apartado anterior/siguiente.
      Arriba: entra al final del apartado anterior.
      Abajo: entra al inicio del apartado siguiente.
    """
    supabase = get_supabase_client()
    habits_df = load_habits(username)

    if habits_df.empty or habit_id not in habits_df["id"].tolist():
        return False, "No encontré ese hábito."

    selected_row = habits_df.loc[habits_df["id"] == habit_id].iloc[0]
    category = str(selected_row["category"])

    if category not in CATEGORIES:
        return False, "Ese hábito tiene un apartado inválido."

    category_index = CATEGORIES.index(category)
    category_habits = habits_df[habits_df["category"] == category].reset_index(drop=True)
    selected_positions = category_habits.index[category_habits["id"] == habit_id].tolist()

    if not selected_positions:
        return False, "No encontré la posición del hábito."

    position = selected_positions[0]

    if direction == "up":
        if position > 0:
            previous_row = category_habits.iloc[position - 1]
            swap_habit_sort_orders(selected_row, previous_row)
            normalize_habit_orders(username)
            return True, "Hábito subido."

        if category_index == 0:
            return False, "Ese hábito ya está hasta arriba."

        new_category = CATEGORIES[category_index - 1]
        new_order = get_next_sort_order(username, new_category)
        (
            supabase
            .table("habits")
            .update({"category": new_category, "sort_order": new_order})
            .eq("id", habit_id)
            .eq("user_name", username)
            .execute()
        )
        sync_habit_logs_metadata(username, habit_id, category=new_category)
        normalize_habit_orders(username)
        return True, f"Hábito movido a {new_category}."

    if direction == "down":
        if position < len(category_habits) - 1:
            next_row = category_habits.iloc[position + 1]
            swap_habit_sort_orders(selected_row, next_row)
            normalize_habit_orders(username)
            return True, "Hábito bajado."

        if category_index == len(CATEGORIES) - 1:
            return False, "Ese hábito ya está hasta abajo."

        new_category = CATEGORIES[category_index + 1]
        # 0 lo coloca al inicio; normalize_habit_orders lo convierte en 1 y
        # recorre el resto del apartado sin perder orden relativo.
        (
            supabase
            .table("habits")
            .update({"category": new_category, "sort_order": 0})
            .eq("id", habit_id)
            .eq("user_name", username)
            .execute()
        )
        sync_habit_logs_metadata(username, habit_id, category=new_category)
        normalize_habit_orders(username)
        return True, f"Hábito movido a {new_category}."

    return False, "Dirección inválida."


def get_habit_active_days(habit) -> list[str]:
    """Días en los que un hábito aplica. Si no hay valor guardado (hábitos
    creados antes de este cambio), se asume que aplica todos los días."""
    value = habit.get("active_days", None) if hasattr(habit, "get") else None
    if not value:
        return list(DAY_LETTERS)
    return list(value)


def get_log_map(logs_df: pd.DataFrame) -> dict:
    if logs_df.empty:
        return {}

    return {
        (row["habit_id"], row["fecha"]): row["valor"]
        for _, row in logs_df.iterrows()
    }


def compute_current_streak(
    habit_id: str,
    active_days: list[str],
    today: date,
    log_map: dict,
    max_lookback_days: int = 3650,
) -> int:
    """Racha actual (días consecutivos cumplidos) de un hábito.

    - Los días en los que el hábito no aplica se saltan: no suman ni
      rompen la racha.
    - Si el día de hoy es aplicable pero todavía no se marca, no se
      rompe la racha (el día sigue en curso); se toma en cuenta desde
      ayer hacia atrás. En cuanto pasa un día aplicable sin marcar, la
      racha se corta ahí.
    """
    day = today
    day_letter = get_day_letter(day)

    if day_letter in active_days:
        completed_today = bool(log_map.get((habit_id, day.isoformat()), 0))
        if not completed_today:
            day = day - timedelta(days=1)
    else:
        day = day - timedelta(days=1)

    streak = 0

    for _ in range(max_lookback_days):
        day_letter = get_day_letter(day)

        if day_letter not in active_days:
            day = day - timedelta(days=1)
            continue

        completed = bool(log_map.get((habit_id, day.isoformat()), 0))

        if not completed:
            break

        streak += 1
        day = day - timedelta(days=1)

    return streak


def build_streak_log_map(
    username: str,
    habits_df: pd.DataFrame,
    base_log_map: dict,
    week_dates: list[date],
) -> dict:
    """Combina el histórico guardado con lo que está marcado actualmente
    en la sesión para calcular rachas en tiempo real.

    Sin esto, las rachas solo ven lo ya guardado en Supabase. Si marcas
    varios días de la semana y todavía no guardas, el streak puede verse
    atrasado o directamente no aparecer.
    """
    merged_log_map = dict(base_log_map)

    for _, habit in habits_df.iterrows():
        habit_id = habit["id"]
        active_days = get_habit_active_days(habit)

        for i, day_letter in enumerate(DAY_LETTERS):
            if day_letter not in active_days:
                continue

            fecha = week_dates[i].isoformat()
            key = f"check_{username}_{habit_id}_{fecha}"

            if key in st.session_state:
                merged_log_map[(habit_id, fecha)] = int(bool(st.session_state[key]))

    return merged_log_map


def ensure_week_state(
    username: str,
    habits_df: pd.DataFrame,
    logs_df: pd.DataFrame,
    week_dates: list[date],
) -> None:
    """Inicializa en st.session_state el valor de cada casilla (hábito x día)
    de la semana a partir de lo guardado en Supabase, sin pisar cambios que
    el usuario ya haya hecho en esta sesión. Se usa tanto en la vista de
    escritorio como en la de celular para que ambas compartan exactamente
    el mismo estado."""
    log_map = get_log_map(logs_df)

    for _, habit in habits_df.iterrows():
        habit_id = habit["id"]

        for i, day_letter in enumerate(DAY_LETTERS):
            fecha = week_dates[i].isoformat()
            key = f"check_{username}_{habit_id}_{fecha}"

            if key not in st.session_state:
                st.session_state[key] = bool(log_map.get((habit_id, fecha), 0))


def build_week_table(
    username: str,
    habits_df: pd.DataFrame,
    week_dates: list[date],
) -> pd.DataFrame:
    """Arma la tabla de la semana completa (todos los hábitos x los 7 días)
    a partir de st.session_state. Los días en los que un hábito no aplica
    quedan como None para no afectar el porcentaje de cumplimiento."""
    records = []

    for _, habit in habits_df.iterrows():
        habit_id = habit["id"]
        habit_name = habit["habit_name"]
        category = habit["category"]
        active_days = get_habit_active_days(habit)

        row = {"id": habit_id, "Apartado": category, "Hábito": habit_name}

        for i, day_letter in enumerate(DAY_LETTERS):
            if day_letter not in active_days:
                row[day_letter] = None
                continue

            fecha = week_dates[i].isoformat()
            key = f"check_{username}_{habit_id}_{fecha}"
            row[day_letter] = bool(st.session_state.get(key, False))

        records.append(row)

    if not records:
        return pd.DataFrame(columns=["id", "Apartado", "Hábito"] + DAY_LETTERS).set_index("id")

    return pd.DataFrame(records).set_index("id")


def resolve_view_mode() -> str:
    """Devuelve 'mobile' o 'desktop'. Por default se detecta solo el tipo de
    dispositivo a partir del User-Agent del navegador (celulares → vista
    optimizada, tablets/PC → vista de escritorio). El botón de "cambiar
    vista" en la parte superior permite forzar la que se prefiera, por si la
    detección automática falla en algún navegador."""
    if "view_mode_override" in st.session_state:
        return st.session_state["view_mode_override"]

    try:
        user_agent = (st.context.headers.get("User-Agent") or "").lower()
    except Exception:
        user_agent = ""

    tablet_tokens = ("ipad", "tablet")
    mobile_tokens = (
        "iphone", "ipod", "android", "mobile",
        "blackberry", "windows phone", "opera mini",
    )

    if any(token in user_agent for token in tablet_tokens):
        return "desktop"

    if any(token in user_agent for token in mobile_tokens):
        return "mobile"

    return "desktop"


def render_habit_manager(username: str, all_logs_df: pd.DataFrame | None = None):
    with st.expander("⚙️ Configuración", expanded=False):
        col_add, col_edit, col_session = st.columns([1, 1.35, 0.7], gap="large")

        with col_add:
            st.subheader("Agregar hábito")

            with st.form("add_habit_form", clear_on_submit=True):
                new_category = st.selectbox("Apartado", CATEGORIES)
                new_habit = st.text_input("Nombre del hábito")
                new_active_days = st.multiselect(
                    "Días en los que aplica",
                    DAY_LETTERS,
                    default=list(DAY_LETTERS),
                    format_func=lambda d: DAY_NAMES_SHORT[d],
                )
                submitted_add = st.form_submit_button("Agregar hábito")

            if submitted_add:
                if new_habit.strip() and new_active_days:
                    add_habit(username, new_category, new_habit.strip(), new_active_days)
                    st.success("Hábito agregado.")
                    st.rerun()
                elif not new_habit.strip():
                    st.warning("Escribe un hábito.")
                else:
                    st.warning("Selecciona al menos un día.")

        with col_edit:
            st.subheader("Editar hábito")

            habits_for_edit = load_habits(username)

            if habits_for_edit.empty:
                st.caption("No hay hábitos para editar.")
            else:
                habits_for_edit = habits_for_edit.copy()
                habits_for_edit["label"] = (
                    habits_for_edit["category"].astype(str)
                    + " · "
                    + habits_for_edit["habit_name"].astype(str)
                )

                habit_ids = habits_for_edit["id"].tolist()
                label_by_id = habits_for_edit.set_index("id")["label"].to_dict()

                # Usar el ID como valor evita errores si dos hábitos tienen el
                # mismo nombre visible. El usuario ve la etiqueta; la app opera
                # con habit_id.
                remembered_id = st.session_state.get("manage_selected_habit_id")
                default_index = habit_ids.index(remembered_id) if remembered_id in habit_ids else 0

                selected_id = st.selectbox(
                    "Selecciona hábito",
                    habit_ids,
                    index=default_index,
                    key="manage_habit_select",
                    format_func=lambda habit_id: label_by_id.get(habit_id, "Hábito"),
                )

                selected_row = habits_for_edit.loc[habits_for_edit["id"] == selected_id].iloc[0]
                st.session_state["manage_selected_habit_id"] = selected_id

                current_category = str(selected_row["category"])
                current_category_index = CATEGORIES.index(current_category) if current_category in CATEGORIES else 0
                current_active_days = get_habit_active_days(selected_row)

                with st.form(f"edit_habit_form_{selected_id}"):
                    edited_habit_name = st.text_input(
                        "Nombre del hábito",
                        value=str(selected_row["habit_name"]),
                        key=f"habit_name_edit_{selected_id}",
                    )
                    edited_category = st.selectbox(
                        "Apartado",
                        CATEGORIES,
                        index=current_category_index,
                        key=f"category_edit_{selected_id}",
                        help="Si cambias el apartado desde aquí, el hábito se manda al final del nuevo apartado. Para una posición exacta usa Subir/Bajar.",
                    )
                    edited_active_days = st.multiselect(
                        "Días en los que aplica",
                        DAY_LETTERS,
                        default=current_active_days,
                        format_func=lambda d: DAY_NAMES_SHORT[d],
                        key=f"active_days_edit_{selected_id}",
                        help="Desmarca los días en los que este hábito no se debe contar.",
                    )
                    submitted_edit = st.form_submit_button("Guardar cambios", use_container_width=True)

                if submitted_edit:
                    clean_name = edited_habit_name.strip()
                    if not clean_name:
                        st.warning("Escribe un nombre válido.")
                    elif not edited_active_days:
                        st.warning("Selecciona al menos un día.")
                    else:
                        update_habit_details(
                            username=username,
                            habit_id=selected_id,
                            habit_name=clean_name,
                            category=edited_category,
                            active_days=edited_active_days,
                        )
                        st.success("Hábito actualizado sin perder histórico ni rachas.")
                        st.rerun()

                st.caption("Orden cronológico")
                move_col1, move_col2 = st.columns(2)

                with move_col1:
                    if st.button("⬆️ Subir", use_container_width=True, key=f"move_up_{selected_id}"):
                        moved, message = move_habit(username, selected_id, "up")
                        if moved:
                            st.success(message)
                            st.rerun()
                        else:
                            st.warning(message)

                with move_col2:
                    if st.button("⬇️ Bajar", use_container_width=True, key=f"move_down_{selected_id}"):
                        moved, message = move_habit(username, selected_id, "down")
                        if moved:
                            st.success(message)
                            st.rerun()
                        else:
                            st.warning(message)

                st.caption("Zona peligrosa")
                if st.button("Eliminar hábito", use_container_width=True, key=f"delete_habit_{selected_id}"):
                    deactivate_habit(selected_id)
                    st.session_state.pop("manage_selected_habit_id", None)
                    st.success("Hábito eliminado de la vista. El histórico se conserva.")
                    st.rerun()

        with col_session:
            st.subheader("Sesión")
            st.write("")

            if all_logs_df is not None and not all_logs_df.empty:
                excel_file = create_excel_download(all_logs_df)

                st.download_button(
                    label="Descargar base de datos",
                    data=excel_file,
                    file_name=f"personal_growth_{username}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

                st.write("")

            if st.button("Cerrar sesión", use_container_width=True):
                st.session_state.clear()
                st.rerun()

def render_tracker_header(current_day_letter: str):
    """Renders the ⭐ D L M X J V S header using the exact same st.columns
    weights as the habit rows below, so both are always pixel-aligned."""
    header_cols = st.columns(TRACKER_COL_WEIGHTS, gap="small")

    with header_cols[0]:
        st.markdown("<div class='tr-head-label' style='text-align:center;'>⭐</div>", unsafe_allow_html=True)

    with header_cols[1]:
        st.markdown("<div class='tr-head-label'>Hábito</div>", unsafe_allow_html=True)

    for i, day_letter in enumerate(DAY_LETTERS):
        with header_cols[i + 2]:
            css_class = "tr-head-day-current" if day_letter == current_day_letter else "tr-head-day"
            st.markdown(f"<div class='{css_class}'>{day_letter}</div>", unsafe_allow_html=True)


def render_tracker(
    username: str,
    habits_df: pd.DataFrame,
    logs_df: pd.DataFrame,
    week_dates: list[date],
    current_day_letter: str,
    today: date,
    streaks: dict,
) -> pd.DataFrame:
    records = []
    log_map = get_log_map(logs_df)
    habit_records = habits_df.to_dict("records")

    render_tracker_header(current_day_letter)

    for category in CATEGORIES:
        category_habits = habits_df[habits_df["category"] == category].copy()

        if category_habits.empty:
            continue

        with st.expander(category, expanded=True, key=f"desktop_cat_{category}"):
            for _, habit in category_habits.iterrows():
                habit_id = habit["id"]
                habit_name = str(habit["habit_name"])
                active_days = get_habit_active_days(habit)
                streak_value = streaks.get(habit_id, 0)

                row = {
                    "id": habit_id,
                    "Apartado": category,
                    "Hábito": habit_name,
                }

                cols = st.columns(TRACKER_COL_WEIGHTS, gap="small")

                with cols[0]:
                    if streak_value >= 3:
                        st.markdown(f"<div class='streak-badge'>⭐{streak_value}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div class='streak-badge-empty'></div>", unsafe_allow_html=True)

                with cols[1]:
                    st.markdown(
                        f"<div class='habit-name'>{html.escape(habit_name)}</div>",
                        unsafe_allow_html=True,
                    )

                for i, day_letter in enumerate(DAY_LETTERS):
                    fecha_date = week_dates[i]
                    fecha = fecha_date.isoformat()

                    # Día en el que el hábito no aplica: se bloquea la celda y no
                    # se cuenta en el porcentaje de cumplimiento.
                    if day_letter not in active_days:
                        with cols[i + 2]:
                            st.markdown("<div class='cell-excluded'>–</div>", unsafe_allow_html=True)
                        row[day_letter] = None
                        continue

                    key = f"check_{username}_{habit_id}_{fecha}"
                    default_value = bool(log_map.get((habit_id, fecha), 0))

                    if key not in st.session_state:
                        st.session_state[key] = default_value

                    # No se permite marcar días futuros, para no adelantar datos.
                    is_future = fecha_date > today

                    with cols[i + 2]:
                        st.checkbox(
                            label=f"{habit_name} {day_letter}",
                            key=key,
                            label_visibility="collapsed",
                            disabled=is_future,
                            on_change=on_habit_checked,
                            args=(
                                username,
                                habit_records,
                                week_dates,
                                habit_name,
                                fecha_date,
                                day_letter,
                                key,
                            ),
                        )

                    row[day_letter] = bool(st.session_state[key])

                records.append(row)

    if not records:
        return pd.DataFrame(columns=["id", "Apartado", "Hábito"] + DAY_LETTERS).set_index("id")

    return pd.DataFrame(records).set_index("id")


def calculate_day_completion(edited_table: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for day in DAY_LETTERS:
        if edited_table.empty:
            percentage = 0
        else:
            # Las celdas excluidas (None) no cuentan para el porcentaje.
            values = edited_table[day].dropna().astype(bool).astype(int).tolist()
            percentage = sum(values) / len(values) if values else 0

        rows.append({
            "Día": day,
            "Cumplimiento": percentage * 100,
        })

    return pd.DataFrame(rows)


def save_week(username: str, edited_table: pd.DataFrame, week_dates: list[date]):
    supabase = get_supabase_client()
    records = []

    if edited_table.empty:
        return

    for habit_id, row in edited_table.iterrows():
        category = row["Apartado"]
        habit_name = row["Hábito"]

        for i, day_letter in enumerate(DAY_LETTERS):
            fecha = week_dates[i]
            cell_value = row[day_letter]

            # Celda excluida para este hábito: no se guarda, no debe afectar
            # el histórico ni el porcentaje de cumplimiento.
            if cell_value is None or (isinstance(cell_value, float) and pd.isna(cell_value)):
                continue

            valor = int(bool(cell_value))

            records.append({
                "user_name": username,
                "fecha": fecha.isoformat(),
                "anio": fecha.year,
                "semana": fecha.isocalendar().week,
                "dia": day_letter,
                "habit_id": habit_id,
                "category": category,
                "habit_name": habit_name,
                "valor": valor,
            })

    if records:
        (
            supabase
            .table("habit_logs")
            .upsert(records, on_conflict="user_name,fecha,habit_id")
            .execute()
        )


def save_single_log(
    username: str,
    habit_id: str,
    habit_name: str,
    category: str,
    fecha: date,
    day_letter: str,
    valor: bool,
):
    """Guarda un solo hábito de forma inmediata.

    Esto convierte el registro diario en una acción de un toque: el usuario
    marca/desmarca y Supabase queda actualizado sin depender del botón de
    "Guardar semana".
    """
    supabase = get_supabase_client()

    record = {
        "user_name": username,
        "fecha": fecha.isoformat(),
        "anio": fecha.year,
        "semana": fecha.isocalendar().week,
        "dia": day_letter,
        "habit_id": habit_id,
        "category": category,
        "habit_name": habit_name,
        "valor": int(bool(valor)),
    }

    (
        supabase
        .table("habit_logs")
        .upsert([record], on_conflict="user_name,fecha,habit_id")
        .execute()
    )


def save_day_snapshot(
    username: str,
    habits_records: list[dict],
    week_dates: list[date],
    day_letter: str,
):
    """Guarda el estado completo de un día.

    Importante para autosave: si solo se guardara el checkbox tocado, el
    histórico quedaría sesgado porque los hábitos no tocados no existirían como
    intentos fallidos. Este snapshot conserva métricas honestas.
    """
    if day_letter not in DAY_LETTERS:
        return

    supabase = get_supabase_client()
    day_index = DAY_LETTERS.index(day_letter)
    fecha = week_dates[day_index]
    records = []

    for habit in habits_records:
        habit_id = habit.get("id")
        habit_name = str(habit.get("habit_name", "Hábito"))
        category = habit.get("category", "")
        active_days = get_habit_active_days(habit)

        if not habit_id or day_letter not in active_days:
            continue

        key = f"check_{username}_{habit_id}_{fecha.isoformat()}"
        valor = int(bool(st.session_state.get(key, False)))

        records.append({
            "user_name": username,
            "fecha": fecha.isoformat(),
            "anio": fecha.year,
            "semana": fecha.isocalendar().week,
            "dia": day_letter,
            "habit_id": habit_id,
            "category": category,
            "habit_name": habit_name,
            "valor": valor,
        })

    if records:
        (
            supabase
            .table("habit_logs")
            .upsert(records, on_conflict="user_name,fecha,habit_id")
            .execute()
        )


def on_habit_checked(
    username: str,
    habits_records: list[dict],
    week_dates: list[date],
    habit_name: str,
    fecha: date,
    day_letter: str,
    key: str,
):
    valor = bool(st.session_state.get(key, False))

    save_day_snapshot(
        username=username,
        habits_records=habits_records,
        week_dates=week_dates,
        day_letter=day_letter,
    )

    st.session_state["_perfect_day_check"] = day_letter
    st.session_state["_perfect_day_date"] = fecha.isoformat()
    st.session_state["_last_autosave_habit"] = habit_name
    st.session_state["_last_autosave_value"] = valor

def get_completion_status(percentage: float) -> tuple[str, str]:
    if percentage >= 100:
        return "Día perfecto", "Cerraste todo lo que tocaba hoy. Protege esa identidad."
    if percentage >= 70:
        return "Buen día", "Ya estás del lado correcto. Remata."
    if percentage >= 40:
        return "Día recuperable", "Todavía puedes salvar el día."
    if percentage > 0:
        return "Arrancaste", "No lo dejes morir aquí. El siguiente check importa."
    return "Sin iniciar", "Haz el primer check. El momentum empieza ahí."


def get_day_completion_counts(edited_table: pd.DataFrame, day_letter: str) -> tuple[int, int, float]:
    if edited_table.empty or day_letter not in edited_table.columns:
        return 0, 0, 0

    values = edited_table[day_letter].dropna().astype(bool).astype(int)
    completed = int(values.sum()) if len(values) else 0
    total = int(len(values))
    percentage = (completed / total * 100) if total else 0
    return completed, total, percentage


def get_week_completion_percentage(edited_table: pd.DataFrame) -> float:
    if edited_table.empty:
        return 0

    semana_values = pd.Series(edited_table[DAY_LETTERS].values.flatten()).dropna().astype(bool).astype(int)
    return semana_values.mean() * 100 if len(semana_values) else 0


def render_today_hero(completed: int, total: int, percentage: float) -> None:
    status, message = get_completion_status(percentage)
    safe_width = max(0, min(100, percentage))

    st.markdown(
        f"""
        <div class="today-hero">
            <div class="today-hero-kicker">Hoy</div>
            <div class="today-hero-main">{completed}/{total} hábitos</div>
            <div class="today-hero-status">{html.escape(status)}</div>
            <div class="today-progress-track">
                <div class="today-progress-fill" style="width:{safe_width:.0f}%"></div>
            </div>
            <div class="today-hero-message">{html.escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_autosave_note() -> None:
    st.markdown(
        "<div class='autosave-note'>● Guardado automático activado</div>",
        unsafe_allow_html=True,
    )


def show_autosave_feedback() -> None:
    habit_name = st.session_state.pop("_last_autosave_habit", None)
    value = st.session_state.pop("_last_autosave_value", None)

    if not habit_name:
        return

    if value:
        st.toast(f"Guardado · {habit_name}", icon="✅")
    else:
        st.toast(f"Actualizado · {habit_name}", icon="↩️")


def maybe_celebrate_perfect_day(
    username: str,
    habits_df: pd.DataFrame,
    week_dates: list[date],
) -> None:
    day_letter = st.session_state.pop("_perfect_day_check", None)
    fecha_iso = st.session_state.pop("_perfect_day_date", None)

    if not day_letter or not fecha_iso:
        return

    edited_table = build_week_table(username, habits_df, week_dates)
    completed, total, percentage = get_day_completion_counts(edited_table, day_letter)

    if total == 0 or percentage < 100:
        return

    celebration_key = f"celebrated_{username}_{fecha_iso}"
    if st.session_state.get(celebration_key, False):
        return

    st.session_state[celebration_key] = True
    st.balloons()
    st.toast(f"Día perfecto · {completed}/{total} completados", icon="🏆")


def build_consistency_heatmap(all_logs_df: pd.DataFrame, days_back: int = 98) -> go.Figure:
    fig = go.Figure()

    if all_logs_df.empty or "fecha" not in all_logs_df.columns or "valor" not in all_logs_df.columns:
        fig.update_layout(
            height=170,
            margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    df = all_logs_df.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    df = df.dropna(subset=["fecha_dt"])

    end_date = get_local_today()
    start_date = end_date - timedelta(days=days_back - 1)
    df = df[(df["fecha_dt"] >= start_date) & (df["fecha_dt"] <= end_date)]

    daily = (
        df.groupby("fecha_dt")
        .agg(done=("valor", lambda values: sum(bool(value) for value in values)), total=("valor", "count"))
        .reset_index()
    )
    daily["rate"] = daily["done"] / daily["total"].where(daily["total"] != 0)

    all_days = pd.DataFrame({
        "fecha_dt": [start_date + timedelta(days=i) for i in range(days_back)]
    })

    daily = all_days.merge(daily, on="fecha_dt", how="left")
    daily["rate"] = daily["rate"].fillna(0).astype(float)
    daily["week"] = ((pd.to_datetime(daily["fecha_dt"]) - pd.to_datetime(start_date)).dt.days // 7).astype(int)
    daily["weekday"] = pd.to_datetime(daily["fecha_dt"]).dt.weekday.astype(int)
    daily["hover"] = daily.apply(
        lambda row: f"{row['fecha_dt'].strftime('%d/%m/%Y')}<br>Consistencia: {row['rate']:.0%}",
        axis=1,
    )

    day_labels = ["L", "M", "X", "J", "V", "S", "D"]
    value_grid = daily.pivot(index="weekday", columns="week", values="rate").reindex(range(7)).fillna(0)
    hover_grid = daily.pivot(index="weekday", columns="week", values="hover").reindex(range(7)).fillna("")

    fig.add_trace(
        go.Heatmap(
            z=value_grid.values,
            x=list(value_grid.columns),
            y=day_labels,
            text=hover_grid.values,
            colorscale=[
                [0.0, "#f1f5f9"],
                [0.25, "#cffafe"],
                [0.50, "#67e8f9"],
                [0.75, "#06b6d4"],
                [1.0, "#0e7490"],
            ],
            showscale=False,
            hovertemplate="%{text}<extra></extra>",
            xgap=3,
            ygap=3,
        )
    )

    fig.update_layout(
        height=185,
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#475569", size=11),
        dragmode=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(autorange="reversed", fixedrange=True, ticks="", showgrid=False),
    )

    return fig


def render_consistency_heatmap(all_logs_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="insight-card-title">Consistencia histórica</div>
        <div class="insight-card-subtitle">Cada cuadro representa tu cumplimiento diario de los últimos 98 días.</div>
        """,
        unsafe_allow_html=True,
    )

    fig = build_consistency_heatmap(all_logs_df)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True,
            "scrollZoom": False,
            "doubleClick": False,
        },
    )

def render_selected_day_banner(selected_day_letter: str, selected_date: date, current_day_letter: str) -> None:
    if selected_day_letter == current_day_letter:
        return

    st.markdown(
        f"""
        <div class='selected-day-banner'>
            Editando {DAY_NAMES_SHORT[selected_day_letter]} · {selected_date.day}/{selected_date.month}. Los cambios también se guardan automático.
        </div>
        """,
        unsafe_allow_html=True,
    )


def create_excel_download(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="BD_Habitos")

    output.seek(0)
    return output


def build_previous_week_summary(
    habits_df: pd.DataFrame,
    all_logs_df: pd.DataFrame,
    previous_week_start: date,
    previous_week_end: date,
    today: date,
) -> dict | None:
    """Resumen ligero de la semana anterior.

    Usa habit_logs como fuente porque ahí están los intentos aplicables ya
    guardados. Si no hay registros, no muestra tarjeta.
    """
    if all_logs_df.empty:
        return None

    df = all_logs_df.copy()
    if "fecha" not in df.columns or "valor" not in df.columns or "habit_id" not in df.columns:
        return None

    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    prev_df = df[
        (df["fecha_dt"] >= previous_week_start)
        & (df["fecha_dt"] <= previous_week_end)
    ].copy()

    if prev_df.empty:
        return None

    prev_df["valor_int"] = prev_df["valor"].astype(bool).astype(int)
    completed = int(prev_df["valor_int"].sum())
    total = int(len(prev_df))
    percentage = (completed / total * 100) if total else 0

    habit_names = habits_df.set_index("id")["habit_name"].to_dict() if not habits_df.empty else {}

    grouped = (
        prev_df.groupby("habit_id", dropna=False)
        .agg(done=("valor_int", "sum"), total=("valor_int", "count"))
        .reset_index()
    )
    grouped["rate"] = grouped["done"] / grouped["total"].replace(0, pd.NA)

    if "habit_name" in prev_df.columns:
        historical_names = (
            prev_df.dropna(subset=["habit_id"])
            .groupby("habit_id")["habit_name"]
            .first()
            .to_dict()
        )
    else:
        historical_names = {}

    grouped["habit_name"] = grouped["habit_id"].map(habit_names)
    grouped["habit_name"] = grouped["habit_name"].fillna(grouped["habit_id"].map(historical_names))
    grouped["habit_name"] = grouped["habit_name"].fillna("Hábito")

    best_habit = "Sin datos"
    if not grouped.empty:
        best_row = grouped.sort_values(["rate", "done", "total"], ascending=[False, False, False]).iloc[0]
        best_habit = f"{best_row['habit_name']} · {int(best_row['done'])}/{int(best_row['total'])}"

    weak_habits = []
    if not grouped.empty:
        weak_df = grouped[grouped["total"] > 0].sort_values(["rate", "done"], ascending=[True, True]).head(2)
        weak_habits = [str(name) for name in weak_df["habit_name"].tolist() if pd.notna(name)]

    log_map = get_log_map(all_logs_df)
    best_streak_name = "Sin datos"
    best_streak_value = 0
    for _, habit in habits_df.iterrows():
        streak_value = compute_current_streak(
            habit_id=habit["id"],
            active_days=get_habit_active_days(habit),
            today=previous_week_end,
            log_map=log_map,
        )
        if streak_value > best_streak_value:
            best_streak_value = streak_value
            best_streak_name = str(habit["habit_name"])

    return {
        "percentage": percentage,
        "completed": completed,
        "total": total,
        "best_habit": best_habit,
        "best_streak": f"{best_streak_name} · ⭐{best_streak_value}" if best_streak_value else "Sin racha",
        "weak_habits": ", ".join(weak_habits) if weak_habits else "Sin datos",
    }


def render_previous_week_summary(summary: dict | None) -> None:
    if not summary:
        return

    st.markdown(
        "<div class='week-summary-card'>"
        "<div class='week-summary-kicker'>Resumen semana anterior</div>"
        "<div class='week-summary-main'>"
        f"<div class='week-summary-percent'>{summary['percentage']:.0f}%</div>"
        f"<div class='week-summary-sub'>Cerraste {summary['completed']} de {summary['total']} hábitos</div>"
        "</div>"
        "<div class='week-summary-grid'>"
        f"<div class='week-summary-chip'><span>Mejor hábito</span>{html.escape(str(summary['best_habit']))}</div>"
        f"<div class='week-summary-chip'><span>Mejor racha</span>{html.escape(str(summary['best_streak']))}</div>"
        f"<div class='week-summary-chip'><span>A mejorar</span>{html.escape(str(summary['weak_habits']))}</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def build_completion_chart(chart_df: pd.DataFrame, height: int = 320, compact_mobile: bool = False) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df["Día"],
            y=chart_df["Cumplimiento"],
            mode="lines+markers+text",
            fill="tozeroy",
            line=dict(color="#06b6d4", width=4, shape="spline", smoothing=0.75),
            marker=dict(size=9, color="#0891b2"),
            fillcolor="rgba(103, 232, 249, 0.28)",
            text=chart_df["Cumplimiento"].round(0).astype(int).astype(str) + "%",
            textposition="top center",
            hovertemplate="Día %{x}<br>Cumplimiento: %{y:.0f}%<extra></extra>",
        )
    )

    chart_margin = dict(l=0, r=0, t=20, b=34) if compact_mobile else dict(l=0, r=10, t=20, b=34)

    fig.update_layout(
        height=height,
        margin=chart_margin,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#0f172a", size=13),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        dragmode=False,
    )

    # Escritorio y móvil: gráfica limpia con solo eje X visible.
    # El rango Y se conserva en 0-100 para que la escala no cambie entre días,
    # pero el eje Y, sus ticks y su grid se ocultan.
    fig.update_yaxes(
        range=[0, 100],
        visible=False,
        fixedrange=True,
        showgrid=False,
        zeroline=False,
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        fixedrange=True,
        showticklabels=True,
        tickmode="array",
        tickvals=DAY_LETTERS,
        ticktext=DAY_LETTERS,
        ticks="",
        automargin=True,
    )

    return fig


def render_desktop_view(
    username: str,
    habits_df: pd.DataFrame,
    logs_df: pd.DataFrame,
    week_dates: list[date],
    current_day_letter: str,
    today: date,
    streaks: dict,
    all_logs_df: pd.DataFrame,
):
    # key="main_layout" lets the CSS force this row to stay side-by-side
    # (never stacked) from tablet size up, so PC and tablet see everything
    # in a single view.
    with st.container(key="main_layout"):
        left, right = st.columns([0.85, 1.35], gap="large")

        with right:
            st.subheader("Tracker semanal")
            st.caption(f"Día actual: {current_day_letter} · los cambios se guardan automático")
            render_autosave_note()

            # key="tracker_scroll" scopes the CSS that keeps every habit row
            # in one line and, on phones, scrolls horizontally instead of
            # breaking the grid.
            tracker_scroll = st.container(height=470, border=False, key="tracker_scroll")

            with tracker_scroll:
                edited_table = render_tracker(
                    username=username,
                    habits_df=habits_df,
                    logs_df=logs_df,
                    week_dates=week_dates,
                    current_day_letter=current_day_letter,
                    today=today,
                    streaks=streaks,
                )

            st.write("")

            if st.button("Guardar todo ahora (respaldo)", use_container_width=True):
                save_week(username, edited_table, week_dates)
                st.success("Semana guardada correctamente. Si ya existía, se actualizó sin duplicados.")
                st.rerun()

        with left:
            chart_df = calculate_day_completion(edited_table)
            cumplimiento_semana = get_week_completion_percentage(edited_table)
            completed_today, total_today, cumplimiento_hoy = get_day_completion_counts(
                edited_table,
                current_day_letter,
            )

            render_today_hero(
                completed=completed_today,
                total=total_today,
                percentage=cumplimiento_hoy,
            )

            m1, m2 = st.columns(2)
            m1.metric("Cumplimiento semana", f"{cumplimiento_semana:.0f}%")
            m2.metric("Cumplimiento hoy", f"{cumplimiento_hoy:.0f}%")

            st.write("")
            st.subheader("Cumplimiento por día")

            fig = build_completion_chart(chart_df, height=300)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                    "scrollZoom": False,
                    "doubleClick": False,
                },
            )

            render_consistency_heatmap(all_logs_df)

def render_mobile_view(
    username: str,
    habits_df: pd.DataFrame,
    logs_df: pd.DataFrame,
    week_dates: list[date],
    current_day_letter: str,
    today: date,
    streaks: dict,
    all_logs_df: pd.DataFrame,
):
    """Vista móvil optimizada para uso diario.

    Prioridad: abrir, marcar hábitos y salir. Los análisis quedan después del
    registro para que no compitan con la acción principal.
    """
    if "mobile_selected_day" not in st.session_state:
        st.session_state["mobile_selected_day"] = current_day_letter

    selectable_days = [
        day_letter
        for i, day_letter in enumerate(DAY_LETTERS)
        if week_dates[i] <= today
    ]

    if not selectable_days:
        selectable_days = [current_day_letter]

    if st.session_state["mobile_selected_day"] not in selectable_days:
        st.session_state["mobile_selected_day"] = current_day_letter

    edited_table = build_week_table(username, habits_df, week_dates)
    habit_records = habits_df.to_dict("records")
    cumplimiento_semana = get_week_completion_percentage(edited_table)
    completed_today, total_today, cumplimiento_hoy = get_day_completion_counts(
        edited_table,
        current_day_letter,
    )

    render_today_hero(
        completed=completed_today,
        total=total_today,
        percentage=cumplimiento_hoy,
    )

    # Selector compacto. El default es hoy; solo se usa para corregir días pasados.
    st.markdown("<div class='mv-day-select-label'>Día a registrar</div>", unsafe_allow_html=True)

    def day_option_label(day_letter: str) -> str:
        day_date = week_dates[DAY_LETTERS.index(day_letter)]
        today_tag = " · Hoy" if day_letter == current_day_letter else ""
        return f"{DAY_NAMES_SHORT[day_letter]} · {day_date.day}/{day_date.month}{today_tag}"

    with st.container(key="mobile_day_dropdown"):
        selected_day_letter = st.selectbox(
            "Día a registrar",
            options=selectable_days,
            index=selectable_days.index(st.session_state["mobile_selected_day"]),
            format_func=day_option_label,
            label_visibility="collapsed",
            key="mobile_day_selectbox",
        )

    if selected_day_letter != st.session_state["mobile_selected_day"]:
        st.session_state["mobile_selected_day"] = selected_day_letter
        st.rerun()

    selected_index = DAY_LETTERS.index(selected_day_letter)
    selected_date = week_dates[selected_index]
    completed_selected, total_selected, cumplimiento_dia_sel = get_day_completion_counts(
        edited_table,
        selected_day_letter,
    )

    render_selected_day_banner(selected_day_letter, selected_date, current_day_letter)
    render_autosave_note()

    st.markdown(
        f"<div class='mv-habit-label'>Hábito · {completed_selected}/{total_selected} completados</div>",
        unsafe_allow_html=True,
    )

    # ---------- Lista móvil: hábitos primero, insights después ----------
    with st.container(key="mobile_tracker"):
        for category in CATEGORIES:
            category_habits = habits_df[habits_df["category"] == category]

            if category_habits.empty:
                continue

            with st.expander(category, expanded=True, key=f"mobile_cat_{category}"):
                for _, habit in category_habits.iterrows():
                    habit_id = habit["id"]
                    habit_name = str(habit["habit_name"])
                    active_days = get_habit_active_days(habit)
                    streak_value = streaks.get(habit_id, 0)

                    label_prefix = f"⭐{streak_value}  " if streak_value >= 3 else "⠀⠀⠀⠀"
                    visible_label = f"{label_prefix}{habit_name}"

                    if selected_day_letter not in active_days:
                        streak_html = (
                            f"<span class='mv-row-streak'>⭐{streak_value}</span>"
                            if streak_value >= 3 else
                            "<span class='mv-row-streak mv-row-streak-empty'></span>"
                        )
                        st.markdown(
                            "<div class='mv-static-habit-row'>"
                            f"{streak_html}"
                            f"<span class='mv-static-habit-name'>{html.escape(habit_name)}</span>"
                            "<span class='mv-static-na'>No aplica</span>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        key = f"check_{username}_{habit_id}_{selected_date.isoformat()}"
                        st.checkbox(
                            label=visible_label,
                            key=key,
                            label_visibility="visible",
                            on_change=on_habit_checked,
                            args=(
                                username,
                                habit_records,
                                week_dates,
                                habit_name,
                                selected_date,
                                selected_day_letter,
                                key,
                            ),
                        )

    st.write("")

    # Botón secundario de respaldo. La experiencia principal ya es autosave.
    if st.button("Guardar todo ahora (respaldo)", use_container_width=True, key="mobile_backup_save_btn"):
        latest_table = build_week_table(username, habits_df, week_dates)
        save_week(username, latest_table, week_dates)
        st.success("Semana guardada correctamente. Si ya existía, se actualizó sin duplicados.")
        st.rerun()

    st.write("")

    # ---------- Análisis después del registro ----------
    st.markdown("<div class='mv-section-title'>Cumplimiento por día</div>", unsafe_allow_html=True)
    chart_df = calculate_day_completion(edited_table)
    fig = build_completion_chart(chart_df, height=235, compact_mobile=True)
    fig.update_layout(
        autosize=True,
        margin=dict(l=0, r=0, t=12, b=34),
        dragmode=False,
        yaxis_visible=False,
    )
    with st.container(key="mobile_chart"):
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
                "scrollZoom": False,
                "doubleClick": False,
                "staticPlot": False,
            },
        )

    st.write("")
    render_consistency_heatmap(all_logs_df)

    st.write("")
    st.markdown(
        f"""
        <div class="mobile-summary-shell">
            <div class="mobile-metrics-stack">
                <div class="mobile-metric-card">
                    <div class="mobile-metric-label">Cumplimiento semana</div>
                    <div class="mobile-metric-value">{cumplimiento_semana:.0f}%</div>
                </div>
                <div class="mobile-metric-card">
                    <div class="mobile-metric-label">Cumplimiento del día seleccionado</div>
                    <div class="mobile-metric-value">{cumplimiento_dia_sel:.0f}%</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def app():
    username = st.session_state["username"]
    display_name = st.session_state["display_name"]

    today = get_local_today()
    week_number = today.isocalendar().week
    week_start = get_week_start(today)
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    week_end = week_dates[-1]
    current_day_letter = get_day_letter(today)

    view_mode = resolve_view_mode()

    st.markdown(
        f"""
        <div class='pg-brand pg-brand-header'>
            <div class='pg-logo-mark' aria-hidden='true'>L</div>
            <div class='pg-title'>{APP_NAME}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    header_left, header_right = st.columns([0.72, 0.28])

    with header_left:
        st.markdown(
            f"<div class='pg-date'>{format_spanish_date(today)} · Semana {week_number}</div>",
            unsafe_allow_html=True,
        )

    with header_right:
        st.markdown(
            f"<div class='pg-user'>Hola {display_name}</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="view_switch_wrap"):
        switch_label = (
            "🖥️ Ver como escritorio" if view_mode == "mobile"
            else "📱 Ver como celular"
        )

        if st.button(switch_label, key="view_switch_btn"):
            st.session_state["view_mode_override"] = "desktop" if view_mode == "mobile" else "mobile"
            st.rerun()

    show_autosave_feedback()

    habits_df = load_habits(username)

    if habits_df.empty:
        st.info("Todavía no tienes hábitos. Agrega uno desde configuración.")
        render_habit_manager(username)
        return

    logs_df = load_week_logs(username, week_start, week_end)
    ensure_week_state(username, habits_df, logs_df, week_dates)

    # Se carga el histórico completo una sola vez: sirve tanto para calcular
    # las rachas (que pueden venir de semanas anteriores) como para el botón
    # de descarga de Excel, evitando pedirlo dos veces.
    all_logs_df = load_all_logs(username)
    all_log_map = get_log_map(all_logs_df)
    streak_log_map = build_streak_log_map(
        username=username,
        habits_df=habits_df,
        base_log_map=all_log_map,
        week_dates=week_dates,
    )

    streaks = {
        habit["id"]: compute_current_streak(
            habit_id=habit["id"],
            active_days=get_habit_active_days(habit),
            today=today,
            log_map=streak_log_map,
        )
        for _, habit in habits_df.iterrows()
    }

    # Se muestra al arranque de semana (domingo/lunes), pero después del flujo
    # diario para no bloquear la acción principal de registrar hábitos.
    previous_summary = None
    days_since_week_start = (today - week_start).days
    if 0 <= days_since_week_start <= 1:
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)
        previous_summary = build_previous_week_summary(
            habits_df=habits_df,
            all_logs_df=all_logs_df,
            previous_week_start=previous_week_start,
            previous_week_end=previous_week_end,
            today=today,
        )

    if view_mode == "mobile":
        render_mobile_view(
            username=username,
            habits_df=habits_df,
            logs_df=logs_df,
            week_dates=week_dates,
            current_day_letter=current_day_letter,
            today=today,
            streaks=streaks,
            all_logs_df=all_logs_df,
        )
    else:
        render_desktop_view(
            username=username,
            habits_df=habits_df,
            logs_df=logs_df,
            week_dates=week_dates,
            current_day_letter=current_day_letter,
            today=today,
            streaks=streaks,
            all_logs_df=all_logs_df,
        )

    maybe_celebrate_perfect_day(username, habits_df, week_dates)
    render_previous_week_summary(previous_summary)
    st.markdown("<div class='settings-spacer'></div>", unsafe_allow_html=True)
    render_habit_manager(username, all_logs_df)


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    app()