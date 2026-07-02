import hashlib
import html
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client


APP_NAME = "Personal Growth"

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


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📈",
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

</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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
            f"<div class='pg-title login-card-title'>{APP_NAME}</div>",
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

    # Solo se ordena por categoría y por sort_order (orden de creación).
    # No se agrega habit_name como criterio para no reordenar alfabéticamente.
    df = df.sort_values(["category", "sort_order"], kind="stable").reset_index(drop=True)

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


def add_habit(username: str, category: str, habit_name: str, active_days: list[str] | None = None):
    supabase = get_supabase_client()
    habit_name = habit_name.strip()
    active_days = active_days or list(DAY_LETTERS)

    existing = (
        supabase
        .table("habits")
        .select("id")
        .eq("user_name", username)
        .eq("category", category)
        .eq("habit_name", habit_name)
        .execute()
    )

    if existing.data:
        supabase.table("habits").update({
            "active": True,
            "active_days": active_days,
        }).eq("id", existing.data[0]["id"]).execute()
        return

    order_response = (
        supabase
        .table("habits")
        .select("sort_order")
        .eq("user_name", username)
        .eq("category", category)
        .execute()
    )

    # El máximo se calcula en Python (no con ORDER BY ... DESC en la base de
    # datos) porque si sort_order llegara a estar guardado como texto, un
    # ORDER BY descendente lo ordenaría alfabéticamente ("9" > "10") y se
    # asignarían números repetidos o fuera de secuencia.
    existing_orders = []
    for row in order_response.data:
        raw_value = row.get("sort_order")
        if raw_value is None:
            continue
        try:
            existing_orders.append(int(raw_value))
        except (TypeError, ValueError):
            continue

    next_order = (max(existing_orders) + 1) if existing_orders else 1

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


def render_habit_manager(username: str):
    with st.expander("⚙️ Gestionar hábitos", expanded=False):
        col_add, col_edit, col_session = st.columns([1, 1.2, 0.7], gap="large")

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
                if new_habit.strip():
                    add_habit(username, new_category, new_habit.strip(), new_active_days)
                    st.success("Hábito agregado.")
                    st.rerun()
                else:
                    st.warning("Escribe un hábito.")

        with col_edit:
            st.subheader("Editar / eliminar hábito")

            habits_for_edit = load_habits(username)

            if habits_for_edit.empty:
                st.caption("No hay hábitos para editar.")
            else:
                habits_for_edit["label"] = (
                    habits_for_edit["category"].astype(str)
                    + " · "
                    + habits_for_edit["habit_name"].astype(str)
                )

                options = habits_for_edit["label"].tolist()
                ids = habits_for_edit["id"].tolist()

                # Recuerda el último hábito seleccionado para que, al recargar
                # la app (agregar/guardar/etc.), el selector no vuelva al
                # primer hábito de la lista por defecto.
                remembered_id = st.session_state.get("manage_selected_habit_id")
                default_index = ids.index(remembered_id) if remembered_id in ids else 0

                selected_label = st.selectbox(
                    "Selecciona hábito",
                    options,
                    index=default_index,
                    key="manage_habit_select",
                )

                selected_row = habits_for_edit.loc[habits_for_edit["label"] == selected_label].iloc[0]
                selected_id = selected_row["id"]
                st.session_state["manage_selected_habit_id"] = selected_id

                current_active_days = get_habit_active_days(selected_row)

                edited_active_days = st.multiselect(
                    "Días en los que aplica",
                    DAY_LETTERS,
                    default=current_active_days,
                    format_func=lambda d: DAY_NAMES_SHORT[d],
                    key=f"active_days_edit_{selected_id}",
                    help="Desmarca los días en los que este hábito no se debe "
                         "contar (esos días quedarán bloqueados y no afectarán "
                         "tu porcentaje de cumplimiento).",
                )

                btn_col1, btn_col2 = st.columns(2)

                with btn_col1:
                    if st.button("Guardar días", use_container_width=True):
                        if edited_active_days:
                            update_habit_active_days(selected_id, edited_active_days)
                            st.success("Días actualizados.")
                            st.rerun()
                        else:
                            st.warning("Selecciona al menos un día.")

                with btn_col2:
                    if st.button("Eliminar hábito", use_container_width=True):
                        deactivate_habit(selected_id)
                        st.session_state.pop("manage_selected_habit_id", None)
                        st.success("Hábito eliminado de la vista. El histórico se conserva.")
                        st.rerun()

        with col_session:
            st.subheader("Sesión")
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

    render_tracker_header(current_day_letter)

    for category in CATEGORIES:
        category_habits = habits_df[habits_df["category"] == category].copy()

        if category_habits.empty:
            continue

        with st.expander(category, expanded=True, key=f"desktop_cat_{category}"):
            for _, habit in category_habits.iterrows():
                habit_id = habit["id"]
                habit_name = habit["habit_name"]
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
                        f"<div class='habit-name'>{habit_name}</div>",
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


def create_excel_download(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="BD_Habitos")

    output.seek(0)
    return output


def build_completion_chart(chart_df: pd.DataFrame, height: int = 320) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df["Día"],
            y=chart_df["Cumplimiento"],
            mode="lines+markers+text",
            fill="tozeroy",
            line=dict(color="#06b6d4", width=4),
            marker=dict(size=9, color="#0891b2"),
            fillcolor="rgba(103, 232, 249, 0.28)",
            text=chart_df["Cumplimiento"].round(0).astype(int).astype(str) + "%",
            textposition="top center",
            hovertemplate="Día %{x}<br>Cumplimiento: %{y:.0f}%<extra></extra>",
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#0f172a", size=13),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
    )

    fig.update_yaxes(
        range=[0, 100],
        showgrid=True,
        gridcolor="#e2e8f0",
        zeroline=False,
        tickformat=".0f",
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
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
            st.caption(f"Día actual: {current_day_letter}")

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

            if st.button("Guardar semana", use_container_width=True, type="primary"):
                save_week(username, edited_table, week_dates)
                st.success("Semana guardada correctamente. Si ya existía, se actualizó sin duplicados.")
                st.rerun()

        with left:
            chart_df = calculate_day_completion(edited_table)

            if edited_table.empty:
                cumplimiento_semana = 0
                cumplimiento_hoy = 0
            else:
                semana_values = edited_table[DAY_LETTERS].values.flatten()
                semana_values = pd.Series(semana_values).dropna().astype(bool).astype(int)
                cumplimiento_semana = semana_values.mean() * 100 if len(semana_values) else 0

                hoy_values = edited_table[current_day_letter].dropna().astype(bool).astype(int)
                cumplimiento_hoy = hoy_values.mean() * 100 if len(hoy_values) else 0

            m1, m2 = st.columns(2)
            m1.metric("Cumplimiento semana", f"{cumplimiento_semana:.0f}%")
            m2.metric("Cumplimiento hoy", f"{cumplimiento_hoy:.0f}%")

            st.write("")
            st.subheader("Cumplimiento por día")

            fig = build_completion_chart(chart_df, height=320)
            st.plotly_chart(fig, use_container_width=True)

            if not all_logs_df.empty:
                excel_file = create_excel_download(all_logs_df)

                st.download_button(
                    label="Descargar base de datos en Excel",
                    data=excel_file,
                    file_name=f"personal_growth_{username}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


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
    """Vista móvil optimizada.

    En celular no se renderiza la tabla de 7 días. Se usa un dropdown para
    elegir un solo día y cada hábito se muestra como fila de 3 columnas:
    racha | texto | checkbox. Esto elimina el desbordamiento horizontal en
    iPhone y mantiene la misma lógica de session_state / guardado.
    """
    if "mobile_selected_day" not in st.session_state:
        st.session_state["mobile_selected_day"] = current_day_letter

    # En móvil se permiten días pasados y el día actual. No se permiten días
    # futuros para no adelantar datos.
    selectable_days = [
        day_letter
        for i, day_letter in enumerate(DAY_LETTERS)
        if week_dates[i] <= today
    ]

    if not selectable_days:
        selectable_days = [current_day_letter]

    if st.session_state["mobile_selected_day"] not in selectable_days:
        st.session_state["mobile_selected_day"] = current_day_letter

    selected_day_letter = st.session_state["mobile_selected_day"]
    selected_index = DAY_LETTERS.index(selected_day_letter)
    selected_date = week_dates[selected_index]

    edited_table = build_week_table(username, habits_df, week_dates)

    if edited_table.empty:
        cumplimiento_semana = 0
        cumplimiento_hoy = 0
        cumplimiento_dia_sel = 0
    else:
        semana_values = pd.Series(edited_table[DAY_LETTERS].values.flatten()).dropna().astype(bool).astype(int)
        cumplimiento_semana = semana_values.mean() * 100 if len(semana_values) else 0

        hoy_values = edited_table[current_day_letter].dropna().astype(bool).astype(int)
        cumplimiento_hoy = hoy_values.mean() * 100 if len(hoy_values) else 0

        dia_sel_values = edited_table[selected_day_letter].dropna().astype(bool).astype(int)
        cumplimiento_dia_sel = dia_sel_values.mean() * 100 if len(dia_sel_values) else 0

    # ---------- Tarjetas de resumen ----------
    with st.container(key="mobile_summary"):
        m1, m2 = st.columns(2)
        m1.metric("Cumplimiento semana", f"{cumplimiento_semana:.0f}%")
        m2.metric("Cumplimiento hoy", f"{cumplimiento_hoy:.0f}%")

    st.write("")

    # ---------- Gráfica visible debajo de tarjetas ----------
    st.markdown("<div class='mv-section-title'>Cumplimiento por día</div>", unsafe_allow_html=True)
    chart_df = calculate_day_completion(edited_table)
    fig = build_completion_chart(chart_df, height=240)
    st.plotly_chart(fig, use_container_width=True)

    st.write("")

    # ---------- Dropdown de día ----------
    st.markdown("<div class='mv-day-select-label'>Selecciona un día</div>", unsafe_allow_html=True)

    def day_option_label(day_letter: str) -> str:
        day_date = week_dates[DAY_LETTERS.index(day_letter)]
        today_tag = " · Hoy" if day_letter == current_day_letter else ""
        return f"{DAY_NAMES_SHORT[day_letter]} · {day_date.day}/{day_date.month}{today_tag}"

    with st.container(key="mobile_day_dropdown"):
        selected_day_letter = st.selectbox(
            "Selecciona un día",
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
    today_tag = " · Hoy" if selected_day_letter == current_day_letter else ""

    # Recalcular cumplimiento del día seleccionado después del selectbox.
    if edited_table.empty:
        cumplimiento_dia_sel = 0
    else:
        dia_sel_values = edited_table[selected_day_letter].dropna().astype(bool).astype(int)
        cumplimiento_dia_sel = dia_sel_values.mean() * 100 if len(dia_sel_values) else 0

    st.markdown(
        f"<div class='mv-selected-day'>{format_spanish_date(selected_date)}{today_tag} "
        f"· Cumplimiento del día: {cumplimiento_dia_sel:.0f}%</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    st.markdown("<div class='mv-habit-label'>Hábito</div>", unsafe_allow_html=True)

    # ---------- Lista móvil: apartado colapsable + racha | hábito | checkbox ----------
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

                    # En móvil NO usamos st.columns para cada hábito.
                    # Streamlit apila/rompe columnas en anchos tipo iPhone y eso
                    # genera desbordamiento horizontal. Cada hábito se renderiza
                    # como una sola fila; el CSS convierte el checkbox nativo en
                    # una card con layout: streak | texto | checkbox.
                    # Prefijo visual de racha. Cuando no hay racha, se usan
                    # espacios Unicode invisibles para reservar el mismo ancho
                    # y que todos los nombres arranquen alineados en móvil.
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
                        fecha = selected_date.isoformat()
                        key = f"check_{username}_{habit_id}_{fecha}"
                        st.checkbox(
                            label=visible_label,
                            key=key,
                            label_visibility="visible",
                        )

    st.write("")

    if st.button("Guardar semana", use_container_width=True, type="primary", key="mobile_save_btn"):
        # Importante: reconstruir después de los widgets para guardar el estado
        # más reciente del checkbox tocado en móvil.
        latest_table = build_week_table(username, habits_df, week_dates)
        save_week(username, latest_table, week_dates)
        st.success("Semana guardada correctamente. Si ya existía, se actualizó sin duplicados.")
        st.rerun()

    st.write("")

    if not all_logs_df.empty:
        excel_file = create_excel_download(all_logs_df)

        st.download_button(
            label="Descargar base de datos en Excel",
            data=excel_file,
            file_name=f"personal_growth_{username}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

def app():
    username = st.session_state["username"]
    display_name = st.session_state["display_name"]

    today = date.today()
    week_number = today.isocalendar().week
    week_start = get_week_start(today)
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    week_end = week_dates[-1]
    current_day_letter = get_day_letter(today)

    view_mode = resolve_view_mode()

    st.markdown(f"<div class='pg-title'>{APP_NAME}</div>", unsafe_allow_html=True)

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

    render_habit_manager(username)

    habits_df = load_habits(username)

    if habits_df.empty:
        st.info("Todavía no tienes hábitos. Agrega uno desde el panel de gestión.")
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


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    app()