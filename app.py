import hashlib
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client


APP_NAME = "Personal Growth"

DAY_LETTERS = ["D", "L", "M", "X", "J", "V", "S"]
CATEGORIES = ["Mañana", "Tarde", "Noche", "Deseables"]
TRACKER_COL_WEIGHTS = [2.8, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42]

SPANISH_DAYS = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
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
        margin: 0 0.1rem;
    }

    .tr-head-day-current {
        text-align: center;
        font-weight: 900;
        color: #0891b2;
        background: #ecfeff;
        border: 1px solid #67e8f9;
        border-radius: 10px;
        padding: 0.4rem 0.05rem;
        margin: 0 0.1rem;
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
    }

    div[data-testid="stCheckbox"] label {
        display: flex;
        justify-content: center;
        align-items: center;
    }

    div[data-testid="stCheckbox"] p {
        display: none;
    }

    div[data-testid="stCheckbox"] input[type="checkbox"] {
        width: 1.15rem;
        height: 1.15rem;
        accent-color: #06b6d4;
        cursor: pointer;
    }

    .stButton button {
        border-radius: 14px;
        font-weight: 800;
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
    df = df.sort_values(["category", "sort_order", "habit_name"]).reset_index(drop=True)

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


def add_habit(username: str, category: str, habit_name: str):
    supabase = get_supabase_client()
    habit_name = habit_name.strip()

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
        supabase.table("habits").update({"active": True}).eq("id", existing.data[0]["id"]).execute()
        return

    order_response = (
        supabase
        .table("habits")
        .select("sort_order")
        .eq("user_name", username)
        .eq("category", category)
        .order("sort_order", desc=True)
        .limit(1)
        .execute()
    )

    if order_response.data:
        next_order = int(order_response.data[0].get("sort_order") or 0) + 1
    else:
        next_order = 1

    supabase.table("habits").insert({
        "user_name": username,
        "category": category,
        "habit_name": habit_name,
        "sort_order": next_order,
        "active": True,
    }).execute()


def deactivate_habit(habit_id: str):
    supabase = get_supabase_client()
    supabase.table("habits").update({"active": False}).eq("id", habit_id).execute()


def get_log_map(logs_df: pd.DataFrame) -> dict:
    if logs_df.empty:
        return {}

    return {
        (row["habit_id"], row["fecha"]): row["valor"]
        for _, row in logs_df.iterrows()
    }


def render_habit_manager(username: str):
    with st.expander("⚙️ Gestionar hábitos", expanded=False):
        col_add, col_delete, col_session = st.columns([1, 1, 0.7], gap="large")

        with col_add:
            st.subheader("Agregar hábito")

            with st.form("add_habit_form", clear_on_submit=True):
                new_category = st.selectbox("Apartado", CATEGORIES)
                new_habit = st.text_input("Nombre del hábito")
                submitted_add = st.form_submit_button("Agregar hábito")

            if submitted_add:
                if new_habit.strip():
                    add_habit(username, new_category, new_habit.strip())
                    st.success("Hábito agregado.")
                    st.rerun()
                else:
                    st.warning("Escribe un hábito.")

        with col_delete:
            st.subheader("Eliminar hábito")

            habits_for_delete = load_habits(username)

            if habits_for_delete.empty:
                st.caption("No hay hábitos para eliminar.")
            else:
                habits_for_delete["label"] = (
                    habits_for_delete["category"].astype(str)
                    + " · "
                    + habits_for_delete["habit_name"].astype(str)
                )

                selected_label = st.selectbox(
                    "Selecciona hábito",
                    habits_for_delete["label"].tolist(),
                )

                selected_id = habits_for_delete.loc[
                    habits_for_delete["label"] == selected_label,
                    "id",
                ].iloc[0]

                if st.button("Eliminar hábito"):
                    deactivate_habit(selected_id)
                    st.success("Hábito eliminado de la vista. El histórico se conserva.")
                    st.rerun()

        with col_session:
            st.subheader("Sesión")
            st.write("")
            if st.button("Cerrar sesión", use_container_width=True):
                st.session_state.clear()
                st.rerun()


def render_tracker_header(current_day_letter: str):
    """Renders the D L M X J V S header using the exact same st.columns
    weights as the habit rows below, so both are always pixel-aligned."""
    header_cols = st.columns(TRACKER_COL_WEIGHTS, gap="small")

    with header_cols[0]:
        st.markdown("<div class='tr-head-label'>Hábito</div>", unsafe_allow_html=True)

    for i, day_letter in enumerate(DAY_LETTERS):
        with header_cols[i + 1]:
            css_class = "tr-head-day-current" if day_letter == current_day_letter else "tr-head-day"
            st.markdown(f"<div class='{css_class}'>{day_letter}</div>", unsafe_allow_html=True)


def render_tracker(
    username: str,
    habits_df: pd.DataFrame,
    logs_df: pd.DataFrame,
    week_dates: list[date],
    current_day_letter: str,
) -> pd.DataFrame:
    records = []
    log_map = get_log_map(logs_df)

    render_tracker_header(current_day_letter)

    for category in CATEGORIES:
        category_habits = habits_df[habits_df["category"] == category].copy()

        if category_habits.empty:
            continue

        st.markdown(
            f"<div class='tracker-section'>{category}</div>",
            unsafe_allow_html=True,
        )

        for _, habit in category_habits.iterrows():
            habit_id = habit["id"]
            habit_name = habit["habit_name"]

            row = {
                "id": habit_id,
                "Apartado": category,
                "Hábito": habit_name,
            }

            cols = st.columns(TRACKER_COL_WEIGHTS, gap="small")

            with cols[0]:
                st.markdown(
                    f"<div class='habit-name'>{habit_name}</div>",
                    unsafe_allow_html=True,
                )

            for i, day_letter in enumerate(DAY_LETTERS):
                fecha = week_dates[i].isoformat()
                key = f"check_{username}_{habit_id}_{fecha}"
                default_value = bool(log_map.get((habit_id, fecha), 0))

                if key not in st.session_state:
                    st.session_state[key] = default_value

                with cols[i + 1]:
                    st.checkbox(
                        label=f"{habit_name} {day_letter}",
                        key=key,
                        label_visibility="collapsed",
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
            values = edited_table[day].astype(bool).astype(int).tolist()
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
            valor = int(bool(row[day_letter]))

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


def app():
    username = st.session_state["username"]
    display_name = st.session_state["display_name"]

    today = date.today()
    week_number = today.isocalendar().week
    week_start = get_week_start(today)
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    week_end = week_dates[-1]
    current_day_letter = get_day_letter(today)

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

    render_habit_manager(username)

    habits_df = load_habits(username)

    if habits_df.empty:
        st.info("Todavía no tienes hábitos. Agrega uno desde el panel de gestión.")
        return

    logs_df = load_week_logs(username, week_start, week_end)

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
                cumplimiento_semana = edited_table[DAY_LETTERS].astype(bool).astype(int).values.mean() * 100
                cumplimiento_hoy = edited_table[current_day_letter].astype(bool).astype(int).mean() * 100

            m1, m2 = st.columns(2)
            m1.metric("Cumplimiento semana", f"{cumplimiento_semana:.0f}%")
            m2.metric("Cumplimiento hoy", f"{cumplimiento_hoy:.0f}%")

            st.write("")
            st.subheader("Cumplimiento por día")

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
                height=320,
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

            st.plotly_chart(fig, use_container_width=True)

            all_logs_df = load_all_logs(username)

            if not all_logs_df.empty:
                excel_file = create_excel_download(all_logs_df)

                st.download_button(
                    label="Descargar base de datos en Excel",
                    data=excel_file,
                    file_name=f"personal_growth_{username}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    app()