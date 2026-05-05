import datetime
import io
import ssl
from typing import Optional
from urllib.request import Request, urlopen

import certifi
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# ===================================================
# SEITENKONFIGURATION
# ===================================================

st.set_page_config(
    page_title="Gold vs Fiat · Emerald Edition",
    page_icon="🏅",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ===================================================
# EMERALD GOLD THEME
# ===================================================

THEME = {
    "bg_app":     "#0B1812",
    "bg_sidebar": "#0F1E15",
    "bg_panel":   "#111F17",
    "bg_card":    "#162B1E",
    "gold":       "#D4AF37",
    "gold_light": "#F0C755",
    "gold_dim":   "#7A641A",
    "text_pri":   "#F2EDD6",
    "text_muted": "#9A8A58",
    "grid":       "#1C3024",
    "spine":      "#2C4A35",
    "zero_line":  "#C9A227",
}

COLORS = {
    "USD": "#5B9BD5",
    "DEM": "#C8C8C8",
    "EUR": "#F4A82A",
    "GBP": "#50C878",
    "JPY": "#FF6B6B",
    "CHF": "#C084FC",
    "CNY": "#FF8C42",
    "NOK": "#22D3EE",
    "ILS": "#6EA8FE",
    "CAD": "#86EFAC",
    "AUD": "#F9A8D4",
    "SEK": "#D9F99D",
    "DKK": "#7DD3FC",
    "INR": "#FCD34D",
    "MXN": "#34D399",
    "ZAR": "#A78BFA",
}

CURRENCY_NAMES = {
    "USD": "US Dollar",
    "DEM": "Deutsche Mark",
    "EUR": "Euro",
    "GBP": "Britisches Pfund",
    "JPY": "Japanischer Yen",
    "CHF": "Schweizer Franken",
    "CNY": "Chines. Renminbi",
    "NOK": "Norweg. Krone",
    "ILS": "Israel. Schekel",
    "CAD": "Kanad. Dollar",
    "AUD": "Austral. Dollar",
    "SEK": "Schwed. Krone",
    "DKK": "Dän. Krone",
    "INR": "Ind. Rupie",
    "MXN": "Mexikan. Peso",
    "ZAR": "Südafrik. Rand",
}

st.markdown(f"""
<style>
    .stApp {{
        background-color: {THEME['bg_app']};
    }}
    [data-testid="stSidebar"] {{
        background-color: {THEME['bg_sidebar']};
        border-right: 1px solid {THEME['gold_dim']};
    }}
    [data-testid="stSidebar"] * {{
        color: {THEME['text_pri']};
    }}
    h1 {{
        color: {THEME['gold_light']} !important;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}
    h2, h3 {{
        color: {THEME['gold']} !important;
    }}
    p, li, .stMarkdown {{
        color: {THEME['text_pri']};
    }}
    .stRadio > label {{
        color: {THEME['gold']} !important;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .stMultiSelect > label {{
        color: {THEME['gold']} !important;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .stButton > button {{
        background-color: {THEME['bg_card']};
        color: {THEME['gold_light']};
        border: 1px solid {THEME['gold_dim']};
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        background-color: {THEME['gold_dim']};
        color: {THEME['bg_app']};
        border-color: {THEME['gold']};
    }}
    hr {{
        border-color: {THEME['gold_dim']} !important;
        opacity: 0.5;
    }}
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: {THEME['bg_app']}; }}
    ::-webkit-scrollbar-thumb {{ background: {THEME['gold_dim']}; border-radius: 3px; }}
    .block-container {{ padding-top: 1.5rem; }}
    /* Checkbox-Grid im Sidebar */
    [data-testid="stSidebar"] .stCheckbox {{
        margin: 1px 0;
    }}
    [data-testid="stSidebar"] .stCheckbox label {{
        padding: 3px 5px;
        border-radius: 4px;
        transition: background 0.15s;
        cursor: pointer;
    }}
    [data-testid="stSidebar"] .stCheckbox label:hover {{
        background: rgba(212, 175, 55, 0.12);
    }}
    [data-testid="stSidebar"] .stCheckbox label p {{
        color: {THEME['text_pri']} !important;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}
</style>
""", unsafe_allow_html=True)


# ===================================================
# KONFIGURATION
# ===================================================

START_DATE = datetime.date(1970, 1, 1)
END_DATE   = datetime.date.today()

DATAHUB_GOLD_URL    = "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly-processed.csv"
GOLD_YAHOO_FALLBACK = "GC=F"

DEM_PER_EUR = 1.95583

DEFAULT_VISIBLE = {"USD", "DEM", "EUR", "GBP", "JPY", "CHF", "CNY", "NOK", "ILS"}

CURRENCIES = {
    "USD": {"fred": None,               "yahoo": None,       "orientation": "currency_per_usd"},
    "DEM": {"fred": "EXGEUS",           "yahoo": None,       "orientation": "currency_per_usd",
            "synthetic_after_euro": True},
    "EUR": {"fred": "DEXUSEU",          "yahoo": "EURUSD=X", "orientation": "usd_per_currency"},
    "GBP": {"fred": "DEXUSUK",          "yahoo": "GBPUSD=X", "orientation": "usd_per_currency"},
    "JPY": {"fred": "DEXJPUS",          "yahoo": "USDJPY=X", "orientation": "currency_per_usd"},
    "CHF": {"fred": "DEXSZUS",          "yahoo": "USDCHF=X", "orientation": "currency_per_usd"},
    "CNY": {"fred": "DEXCHUS",          "yahoo": "USDCNY=X", "orientation": "currency_per_usd"},
    "NOK": {"fred": "DEXNOUS",          "yahoo": "USDNOK=X", "orientation": "currency_per_usd"},
    "ILS": {"fred": "CCUSMA02ILM618N",  "yahoo": "USDILS=X", "orientation": "currency_per_usd",
            "min_start": "1986-01-01"},
    "CAD": {"fred": "DEXCAUS",          "yahoo": "USDCAD=X", "orientation": "currency_per_usd"},
    "AUD": {"fred": "DEXUSAL",          "yahoo": "AUDUSD=X", "orientation": "usd_per_currency"},
    "SEK": {"fred": "DEXSDUS",          "yahoo": "USDSEK=X", "orientation": "currency_per_usd"},
    "DKK": {"fred": "DEXDNUS",          "yahoo": "USDDKK=X", "orientation": "currency_per_usd"},
    "INR": {"fred": "DEXINUS",          "yahoo": "USDINR=X", "orientation": "currency_per_usd"},
    "MXN": {"fred": "DEXMXUS",          "yahoo": "USDMXN=X", "orientation": "currency_per_usd"},
    "ZAR": {"fred": "DEXSFUS",          "yahoo": "USDZAR=X", "orientation": "currency_per_usd"},
}

TIME_RANGE_LABELS = [
    "All time", "40 Jahre", "30 Jahre", "25 Jahre",
    "10 Jahre", "5 Jahre", "2 Jahre", "Seit 2024",
    "1 Jahr", "YTD",
]


# ===================================================
# DATENFUNKTIONEN
# ===================================================

def read_csv_robust(url: str) -> pd.DataFrame:
    errors = []

    try:
        return pd.read_csv(url)
    except Exception as exc:
        errors.append(f"pandas.read_csv: {exc}")

    try:
        import requests
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))
    except Exception as exc:
        errors.append(f"requests: {exc}")

    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=30, context=context) as resp:
            content = resp.read()
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        errors.append(f"urllib/certifi: {exc}")

    raise RuntimeError("CSV konnte nicht geladen werden:\n" + "\n".join(errors))


def to_monthly(series: pd.Series) -> pd.Series:
    series = series.copy()
    series.index = pd.to_datetime(series.index)
    series = series.sort_index().dropna()
    return series.resample("ME").last().ffill()


def get_datahub_gold_series(start_date, end_date) -> pd.Series:
    df = read_csv_robust(DATAHUB_GOLD_URL)
    if "Date" not in df.columns or "Price" not in df.columns:
        raise ValueError(f"Unerwartete DataHub-Spalten: {df.columns.tolist()}")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    series = pd.Series(df["Price"].values, index=df["Date"], name="Gold_USD_per_oz")
    series = series.loc[
        (series.index >= pd.Timestamp(start_date)) &
        (series.index <= pd.Timestamp(end_date))
    ]
    series = to_monthly(series)
    if series.empty:
        raise ValueError("DataHub-Goldserie enthält keine nutzbaren Daten.")
    return series


def get_fred_series(code: str, start_date, end_date, name: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}"
    df = read_csv_robust(url)
    date_col  = "observation_date" if "observation_date" in df.columns else df.columns[0]
    value_col = code if code in df.columns else df.columns[-1]
    df[date_col] = pd.to_datetime(df[date_col])
    values = pd.to_numeric(df[value_col], errors="coerce")
    series = pd.Series(values.values, index=df[date_col], name=name)
    series = series.loc[
        (series.index >= pd.Timestamp(start_date)) &
        (series.index <= pd.Timestamp(end_date))
    ]
    series = to_monthly(series)
    if series.empty:
        raise ValueError(f"FRED-Serie {code} enthält keine nutzbaren Daten.")
    return series


def get_yahoo_series(ticker: str, start_date, end_date, name: str) -> pd.Series:
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
    if data.empty:
        raise ValueError(f"Yahoo-Ticker {ticker} enthält keine Daten.")
    if isinstance(data.columns, pd.MultiIndex):
        level_0 = data.columns.get_level_values(0)
        selected = data["Adj Close"] if "Adj Close" in level_0 else data["Close"]
        series = selected[ticker] if isinstance(selected, pd.DataFrame) and ticker in selected.columns else (
            selected.iloc[:, 0] if isinstance(selected, pd.DataFrame) else selected
        )
    else:
        series = data["Adj Close"] if "Adj Close" in data.columns else data["Close"]
    series.name = name
    series = to_monthly(series)
    if series.empty:
        raise ValueError(f"Yahoo-Ticker {ticker} enthält keine nutzbaren Daten.")
    return series


def get_series_with_fallback(name, fred_code, yahoo_ticker, start_date, end_date) -> pd.Series:
    if fred_code:
        try:
            return get_fred_series(fred_code, start_date, end_date, name)
        except Exception:
            pass
    if yahoo_ticker:
        try:
            return get_yahoo_series(yahoo_ticker, start_date, end_date, name)
        except Exception:
            pass
    raise ValueError(f"Keine Datenquelle für {name} verfügbar.")


def build_dem_series(start_date, end_date, full_index) -> pd.Series:
    dem_hist = get_fred_series("EXGEUS", start_date, end_date, "DEM").reindex(full_index).ffill()
    eur_usd  = get_fred_series("DEXUSEU", start_date, end_date, "EURUSD").reindex(full_index).ffill()
    dem_from_eur = DEM_PER_EUR / eur_usd
    dem = dem_hist.copy()
    dem.loc[dem.index >= pd.Timestamp("1999-01-01")] = dem_from_eur.loc[dem.index >= pd.Timestamp("1999-01-01")]
    dem.name = "DEM"
    if dem.dropna().empty:
        raise ValueError("DEM-Serie enthält keine nutzbaren Daten.")
    return dem


# ===================================================
# DATEN LADEN (GECACHT)
# ===================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    try:
        gold_usd = get_datahub_gold_series(START_DATE, END_DATE)
    except Exception:
        gold_usd = get_yahoo_series(GOLD_YAHOO_FALLBACK, START_DATE, END_DATE, "Gold_USD_per_oz")

    full_index = gold_usd.index

    fx_data = {}
    for cur, cfg in CURRENCIES.items():
        if cur == "USD":
            fx_data[cur] = pd.Series(1.0, index=full_index, name="USD")
            continue
        try:
            if cur == "DEM" and cfg.get("synthetic_after_euro", False):
                s = build_dem_series(START_DATE, END_DATE, full_index)
            else:
                s = get_series_with_fallback(cur, cfg["fred"], cfg["yahoo"], START_DATE, END_DATE)
                s = s.reindex(full_index).ffill()
            fx_data[cur] = s.rename(cur)
        except Exception:
            pass

    fx_df = pd.concat(fx_data.values(), axis=1)

    gold_local = pd.DataFrame(index=full_index)
    for cur, cfg in CURRENCIES.items():
        if cur not in fx_df.columns:
            continue
        if cur == "USD":
            gold_local[cur] = gold_usd
            continue
        fx = fx_df[cur]
        if cfg["orientation"] == "currency_per_usd":
            gold_local[cur] = gold_usd * fx
        elif cfg["orientation"] == "usd_per_currency":
            gold_local[cur] = gold_usd / fx

    ounces = 1.0 / gold_local
    order = [
        cur for cur in CURRENCIES
        if cur in ounces.columns and not ounces[cur].dropna().empty
    ]

    return ounces, order, full_index


# ===================================================
# ZEITRAUM-LOGIK
# ===================================================

def get_period_bounds(label: str, full_index):
    x_end = full_index.max()

    if label == "All time":      x_start = pd.Timestamp(START_DATE)
    elif label == "40 Jahre":    x_start = x_end - pd.DateOffset(years=40)
    elif label == "30 Jahre":    x_start = x_end - pd.DateOffset(years=30)
    elif label == "25 Jahre":    x_start = x_end - pd.DateOffset(years=25)
    elif label == "10 Jahre":    x_start = x_end - pd.DateOffset(years=10)
    elif label == "5 Jahre":     x_start = x_end - pd.DateOffset(years=5)
    elif label == "2 Jahre":     x_start = x_end - pd.DateOffset(years=2)
    elif label == "Seit 2024":   x_start = pd.Timestamp("2024-01-01")
    elif label == "1 Jahr":      x_start = x_end - pd.DateOffset(years=1)
    elif label == "YTD":         x_start = pd.Timestamp(datetime.date(x_end.year, 1, 1))
    else:                        x_start = pd.Timestamp(START_DATE)

    return max(x_start, pd.Timestamp(START_DATE)), x_end


def compute_period_data(label, ounces, currency_order, full_index):
    x_start, x_end = get_period_bounds(label, full_index)
    display_pct  = pd.DataFrame(index=full_index)
    period_stats = {}

    for cur in currency_order:
        s = ounces[cur].dropna()
        if s.empty:
            continue

        cfg = CURRENCIES.get(cur, {})
        eff_start = x_start
        if cfg.get("min_start"):
            eff_start = max(eff_start, pd.Timestamp(cfg["min_start"]))

        s_window = s[(s.index >= eff_start) & (s.index <= x_end)]
        if s_window.empty:
            continue

        base  = s_window.iloc[0]
        rel_s = (ounces[cur] / base - 1.0) * 100.0
        rel_s = rel_s.where((rel_s.index >= eff_start) & (rel_s.index <= x_end))
        display_pct[cur] = rel_s

        last = rel_s.dropna()
        if last.empty:
            continue
        period_stats[cur] = {
            "start":    s_window.index[0],
            "end":      s_window.index[-1],
            "loss_pct": last.iloc[-1],
        }

    return x_start, x_end, display_pct, period_stats


# ===================================================
# SESSION STATE  (wird nach load_all_data initialisiert)
# ===================================================


# ===================================================
# HEADER
# ===================================================

st.markdown(
    f"<h1>⚖ Gold vs Fiat <span style='font-size:0.5em; color:{THEME['text_muted']}; font-weight:400;'>"
    f"· Emerald Edition</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:{THEME['text_muted']}; margin-top:-14px; margin-bottom:8px;'>"
    f"Kaufkraftänderung von Fiat-Währungen relativ zu 1 oz Gold · Stand {END_DATE.strftime('%B %Y')}"
    f"</p>",
    unsafe_allow_html=True,
)


# ===================================================
# DATEN LADEN
# ===================================================

with st.spinner("Daten werden geladen — FRED, DataHub, Yahoo …"):
    ounces, currency_order, full_index = load_all_data()

# Pro-Währung Checkbox-State initialisieren (nur beim ersten Laden)
for _cur in currency_order:
    if f"chk_{_cur}" not in st.session_state:
        st.session_state[f"chk_{_cur}"] = _cur in DEFAULT_VISIBLE


# ===================================================
# SIDEBAR
# ===================================================

with st.sidebar:
    st.markdown(
        f"<p style='color:{THEME['gold']}; font-weight:700; font-size:1.1rem; "
        f"letter-spacing:1px; margin-bottom:4px;'>EINSTELLUNGEN</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    period = st.radio(
        "Zeitraum",
        TIME_RANGE_LABELS,
        index=0,
    )

    st.divider()

    st.markdown(
        f"<p style='color:{THEME['gold']}; font-weight:600; font-size:0.8rem; "
        f"letter-spacing:0.8px; margin-bottom:6px;'>WÄHRUNGEN</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Alle an", use_container_width=True):
            for _c in currency_order:
                st.session_state[f"chk_{_c}"] = True
            st.rerun()
    with col_b:
        if st.button("Alle aus", use_container_width=True):
            for _c in currency_order:
                st.session_state[f"chk_{_c}"] = False
            st.rerun()

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # 3-Spalten-Checkbox-Grid
    for _row in range(0, len(currency_order), 3):
        _row_curs = currency_order[_row:_row + 3]
        _cols = st.columns(3)
        for _ci, _cur in enumerate(_row_curs):
            with _cols[_ci]:
                st.checkbox(_cur, key=f"chk_{_cur}")

    selected = [c for c in currency_order if st.session_state.get(f"chk_{c}", False)]

    st.divider()
    st.markdown(
        f"<p style='color:{THEME['text_muted']}; font-size:0.75rem;'>"
        f"Datenquellen: FRED St. Louis · DataHub · Yahoo Finance<br>"
        f"DEM ab 1999 synthetisch via EUR-Fixkurs (1,95583)</p>",
        unsafe_allow_html=True,
    )


# ===================================================
# CHART
# ===================================================

x_start, x_end, display_pct, period_stats = compute_period_data(
    period, ounces, currency_order, full_index
)

visible = selected or []

fig = go.Figure()

for cur in currency_order:
    if cur not in visible:
        continue
    if cur not in display_pct.columns:
        continue

    y = display_pct[cur].dropna()
    if y.empty:
        continue

    fig.add_trace(go.Scatter(
        x=y.index,
        y=y.values,
        name=cur,
        line=dict(color=COLORS.get(cur, THEME["text_pri"]), width=2.2),
        hovertemplate=(
            f"<b style='color:{COLORS.get(cur, THEME['text_pri'])};'>{cur}</b><br>"
            "%{x|%Y-%m}<br>"
            "<b>%{y:.1f} %</b><extra></extra>"
        ),
    ))

fig.add_hline(
    y=0,
    line_dash="dash",
    line_color=THEME["zero_line"],
    line_width=1.5,
    opacity=0.9,
)

fig.update_layout(
    plot_bgcolor=THEME["bg_panel"],
    paper_bgcolor=THEME["bg_app"],
    font=dict(color=THEME["text_pri"], family="sans-serif", size=12),
    title=dict(
        text=f"Kaufkraftänderung vs. 1 oz Gold  ·  {period}",
        font=dict(color=THEME["gold_light"], size=15, family="sans-serif"),
        x=0.01,
        xanchor="left",
        y=0.97,
    ),
    xaxis=dict(
        title="Datum",
        title_font=dict(color=THEME["text_muted"], size=11),
        tickfont=dict(color=THEME["text_muted"]),
        gridcolor=THEME["grid"],
        showgrid=True,
        linecolor=THEME["spine"],
        range=[x_start, x_end],
        rangeslider=dict(visible=False),
    ),
    yaxis=dict(
        title="Kaufkraftänderung in %  (< 0 = Verlust gegenüber Gold)",
        title_font=dict(color=THEME["text_muted"], size=11),
        tickfont=dict(color=THEME["text_muted"]),
        gridcolor=THEME["grid"],
        showgrid=True,
        linecolor=THEME["spine"],
        ticksuffix=" %",
        zerolinecolor=THEME["spine"],
        zerolinewidth=1,
    ),
    legend=dict(
        bgcolor=THEME["bg_card"],
        bordercolor=THEME["gold_dim"],
        borderwidth=1,
        font=dict(color=THEME["text_pri"], size=11),
        orientation="v",
        x=1.01,
        xanchor="left",
        y=1,
        yanchor="top",
    ),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor=THEME["bg_card"],
        bordercolor=THEME["gold_dim"],
        font=dict(color=THEME["text_pri"]),
    ),
    margin=dict(l=60, r=20, t=55, b=55),
    height=560,
)

st.plotly_chart(fig, width="stretch")


# ===================================================
# AUSWERTUNGS-TABELLE
# ===================================================

visible_stats = {
    cur: v for cur, v in period_stats.items() if cur in visible
}

if visible_stats:
    sorted_stats = sorted(visible_stats.items(), key=lambda x: x[1]["loss_pct"])

    rows_html = ""
    for cur, v in sorted_stats:
        color     = COLORS.get(cur, THEME["text_pri"])
        full_name = CURRENCY_NAMES.get(cur, cur)
        pct       = v["loss_pct"]
        sign      = "+" if pct >= 0 else ""
        pct_color = "#50C878" if pct >= 0 else "#FF6B6B"
        start     = v["start"].strftime("%Y-%m")
        end       = v["end"].strftime("%Y-%m")
        rows_html += f"""
        <tr style="border-bottom:1px solid {THEME['bg_panel']};">
            <td style="padding:6px 12px; white-space:nowrap;">
                <span style="color:{color}; font-size:14px; vertical-align:middle;">&#9679;</span>
                <span style="color:{THEME['text_pri']}; font-weight:600; margin-left:6px;">{full_name}</span>
                <span style="color:{THEME['text_muted']}; font-size:0.8em; margin-left:4px;">({cur})</span>
            </td>
            <td style="padding:6px 12px; text-align:right; font-family:monospace; color:{pct_color}; font-weight:700;">
                {sign}{pct:.1f}&nbsp;%
            </td>
            <td style="padding:6px 12px; text-align:right; font-family:monospace; color:{THEME['text_muted']};">
                {start}
            </td>
            <td style="padding:6px 12px; text-align:right; font-family:monospace; color:{THEME['text_muted']};">
                {end}
            </td>
        </tr>
        """

    inner_html = f"""
    <div style="background:{THEME['bg_card']}; border:1px solid {THEME['gold_dim']};
                border-radius:8px; padding:0; overflow:hidden;">
        <div style="padding:14px 16px 8px 16px;">
            <span style="color:{THEME['gold_light']}; font-size:1rem; font-weight:700; letter-spacing:0.3px;">
                Auswertung &middot; {period}
            </span>
        </div>
        <table style="width:100%; border-collapse:collapse; margin-top:2px;">
            <thead>
                <tr style="background:{THEME['bg_panel']}; border-bottom:1px solid {THEME['gold_dim']};">
                    <th style="padding:7px 12px; text-align:left; color:{THEME['text_muted']};
                               font-size:0.78rem; font-weight:600; letter-spacing:0.5px;">W&Auml;HRUNG</th>
                    <th style="padding:7px 12px; text-align:right; color:{THEME['text_muted']};
                               font-size:0.78rem; font-weight:600; letter-spacing:0.5px;">KAUFKRAFT</th>
                    <th style="padding:7px 12px; text-align:right; color:{THEME['text_muted']};
                               font-size:0.78rem; font-weight:600; letter-spacing:0.5px;">VON</th>
                    <th style="padding:7px 12px; text-align:right; color:{THEME['text_muted']};
                               font-size:0.78rem; font-weight:600; letter-spacing:0.5px;">BIS</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """

    full_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {THEME['bg_app']};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
    padding: 4px 0 8px 0;
  }}
</style>
</head>
<body>{inner_html}</body>
</html>"""

    n_rows = len(sorted_stats)
    iframe_height = 58 + 38 + n_rows * 37 + 16
    st.iframe(full_doc, height=iframe_height)

elif not visible:
    st.markdown(
        f"<p style='color:{THEME['text_muted']}; margin-top:12px;'>"
        "Keine Währung ausgewählt. Wähle links eine oder mehrere Währungen aus."
        "</p>",
        unsafe_allow_html=True,
    )
