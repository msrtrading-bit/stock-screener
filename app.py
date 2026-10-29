import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Growth + Momentum Screener", page_icon="📈", layout="wide")

WEIGHTS = {"Rewizje prognoz": 25, "Wzrost biznesu": 20, "Momentum kursu": 20, "Jakość biznesu": 15, "Wycena": 15, "Free cash flow": 5}

st.title("Growth + Momentum Stock Screener")
st.caption("Wstępna selekcja akcji • scoring 0–100 • dane rynkowe z Yahoo Finance")
st.warning("To narzędzie analityczne, nie rekomendacja inwestycyjna. Dane mogą być opóźnione, niepełne lub błędne. Ocena rewizji prognoz jest ręczna.")

with st.sidebar:
    st.header("Ustawienia")
    min_score = st.slider("Minimalny wynik", 0, 100, 75, 5)
    min_market_cap = st.number_input("Min. kapitalizacja (mln USD)", min_value=0, value=200, step=100)
    min_dollar_volume = st.number_input("Min. średni obrót dzienny (mln USD)", min_value=0.0, value=2.0, step=1.0)
    st.divider()
    st.caption("Wagi scoringu")
    for k, v in WEIGHTS.items():
        st.write(f"{k}: **{v}%**")

default_tickers = "GOOGL, NVDA, MSFT, AMZN, META, AVGO, PLTR, TSM, MELI, SHOP"
tickers_raw = st.text_input("Tickery (oddziel przecinkami)", default_tickers)
uploaded = st.file_uploader("Lub wgraj CSV z tickerami (kolumna: ticker)", type=["csv"])
if uploaded:
    try:
        upload_df = pd.read_csv(uploaded)
        col = next((c for c in upload_df.columns if c.lower() == "ticker"), None)
        if col:
            tickers_raw = ",".join(upload_df[col].dropna().astype(str).tolist())
        else:
            st.error("CSV musi zawierać kolumnę 'ticker'.")
    except Exception as exc:
        st.error(f"Nie udało się odczytać CSV: {exc}")

tickers = list(dict.fromkeys(t.strip().upper() for t in tickers_raw.split(",") if t.strip()))

def safe_num(x):
    try:
        return float(x) if x is not None and np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan

def score_growth(revenue, earnings):
    vals = []
    for x, cuts in [(revenue, [-.05, 0, .08, .20, .35]), (earnings, [-.10, 0, .08, .20, .40])]:
        if pd.notna(x):
            vals.append(sum(x >= c for c in cuts))
    return int(round(np.mean(vals))) if vals else 0

def score_valuation(pe, peg):
    if pd.isna(pe) or pe <= 0:
        return 2
    if pd.notna(peg) and peg > 0:
        return 5 if peg < 1 else 4 if peg < 1.5 else 3 if peg < 2.5 else 2 if peg < 4 else 1
    return 5 if pe < 15 else 4 if pe < 25 else 3 if pe < 35 else 2 if pe < 50 else 1

def analyze(ticker):
    try:
        obj = yf.Ticker(ticker)
        info = obj.get_info()
        hist = obj.history(period="2y", auto_adjust=True)
        if hist.empty:
            return {"Ticker": ticker, "Status": "Brak danych"}
        close = hist["Close"].dropna()
        price = float(close.iloc[-1])
        ret6 = price / float(close.iloc[-min(126, len(close))]) - 1 if len(close) > 20 else np.nan
        ret12 = price / float(close.iloc[-min(252, len(close))]) - 1 if len(close) > 20 else np.nan
        ma200 = float(close.tail(200).mean()) if len(close) >= 200 else np.nan
        above200 = bool(price > ma200) if pd.notna(ma200) else False
        cap = safe_num(info.get("marketCap"))
        avg_vol = safe_num(info.get("averageDailyVolume10Day") or info.get("averageVolume"))
        dollar_vol = price * avg_vol if pd.notna(avg_vol) else np.nan
        revenue = safe_num(info.get("revenueGrowth"))
        earnings = safe_num(info.get("earningsGrowth"))
        fcf = safe_num(info.get("freeCashflow"))
        pe, peg = safe_num(info.get("forwardPE")), safe_num(info.get("pegRatio"))
        roe, margin, debt = safe_num(info.get("returnOnEquity")), safe_num(info.get("operatingMargins")), safe_num(info.get("debtToEquity"))
        growth_score = score_growth(revenue, earnings)
        momentum_score = (2 if pd.notna(ret6) and ret6 > 0 else 0) + (2 if pd.notna(ret12) and ret12 > 0 else 0) + (1 if above200 else 0)
        quality = []
        if pd.notna(roe): quality.append(5 if roe > .25 else 4 if roe > .15 else 3 if roe > .08 else 2 if roe > 0 else 0)
        if pd.notna(margin): quality.append(5 if margin > .30 else 4 if margin > .20 else 3 if margin > .10 else 2 if margin > 0 else 0)
        if pd.notna(debt): quality.append(5 if debt < 30 else 4 if debt < 70 else 3 if debt < 120 else 1)
        quality_score = int(round(np.mean(quality))) if quality else 0
        fcf_score = 0 if pd.isna(fcf) else 5 if fcf > 0 and pd.notna(cap) and cap > 0 and fcf / cap > .04 else 4 if fcf > 0 else 1
        return {
            "Ticker": ticker, "Nazwa": info.get("shortName", ticker), "Cena": price,
            "Market cap (mln USD)": cap / 1e6 if pd.notna(cap) else np.nan,
            "Obrót dzienny (mln USD)": dollar_vol / 1e6 if pd.notna(dollar_vol) else np.nan,
            "Wzrost przychodów r/r": revenue, "Wzrost zysków": earnings,
            "Zwrot 6M": ret6, "Zwrot 12M": ret12, "Powyżej MA200": above200,
            "Forward P/E": pe, "PEG": peg, "ROE": roe, "Marża operacyjna": margin,
            "FCF (mln USD)": fcf / 1e6 if pd.notna(fcf) else np.nan,
            "Score rewizji (ręczny)": 3, "Score growth": growth_score, "Score momentum": momentum_score,
            "Score quality": quality_score, "Score wyceny": score_valuation(pe, peg), "Score FCF": fcf_score, "Status": "OK"
        }
    except Exception as exc:
        return {"Ticker": ticker, "Status": f"Błąd: {str(exc)[:100]}"}

def calculate_score(df):
    df = df.copy()
    df["Wynik /100"] = (
        df["Score rewizji (ręczny)"].fillna(3) * 5 +
        df["Score growth"].fillna(0) * 4 +
        df["Score momentum"].fillna(0) * 4 +
        df["Score quality"].fillna(0) * 3 +
        df["Score wyceny"].fillna(0) * 3 +
        df["Score FCF"].fillna(0) * 1
    ).round(1)
    df["Filtr kapitalizacji"] = df["Market cap (mln USD)"].fillna(0) >= min_market_cap
    df["Filtr płynności"] = df["Obrót dzienny (mln USD)"].fillna(0) >= min_dollar_volume
    df["Decyzja systemu"] = np.where((df["Wynik /100"] >= min_score) & df["Filtr kapitalizacji"] & df["Filtr płynności"] & df["Powyżej MA200"].eq(True), "KANDYDAT DO ANALIZY", "OBSERWUJ / ODRZUĆ")
    return df

if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

if st.button("🔎 Pobierz dane i oblicz ranking", type="primary", use_container_width=True):
    if not tickers:
        st.error("Wpisz co najmniej jeden ticker.")
    else:
        rows, progress, status = [], st.progress(0), st.empty()
        for i, ticker in enumerate(tickers):
            status.write(f"Analizuję {ticker} ({i+1}/{len(tickers)})…")
            rows.append(analyze(ticker))
            progress.progress((i + 1) / len(tickers))
        st.session_state.results = calculate_score(pd.DataFrame(rows))
        progress.empty()
        status.empty()

if not st.session_state.results.empty:
    df = st.session_state.results.copy()
    st.subheader("Ranking")
    st.caption("Score rewizji prognoz jest ręczny. Domyślne 3/5 to neutralny placeholder, nie sygnał rynkowy.")
    edited = st.data_editor(df, use_container_width=True, hide_index=True,
        disabled=[c for c in df.columns if c != "Score rewizji (ręczny)"],
        column_config={
            "Wynik /100": st.column_config.NumberColumn(format="%.1f"),
            "Wzrost przychodów r/r": st.column_config.NumberColumn(format="%.1%"),
            "Wzrost zysków": st.column_config.NumberColumn(format="%.1%"),
            "Zwrot 6M": st.column_config.NumberColumn(format="%.1%"),
            "Zwrot 12M": st.column_config.NumberColumn(format="%.1%"),
            "ROE": st.column_config.NumberColumn(format="%.1%"),
            "Marża operacyjna": st.column_config.NumberColumn(format="%.1%"),
            "Score rewizji (ręczny)": st.column_config.NumberColumn(min_value=0, max_value=5, step=1)
        }, key="stock_editor")
    edited = calculate_score(edited)
    st.session_state.results = edited
    c1, c2, c3 = st.columns(3)
    c1.metric("Spółki przeanalizowane", len(edited))
    c2.metric("Kandydaci do analizy", int(edited["Decyzja systemu"].eq("KANDYDAT DO ANALIZY").sum()))
    c3.metric("Średni score", f"{edited['Wynik /100'].mean():.1f}/100")
    cols = ["Ticker", "Nazwa", "Cena", "Wynik /100", "Decyzja systemu", "Zwrot 6M", "Zwrot 12M", "Wzrost przychodów r/r", "Forward P/E"]
    st.subheader("Skrócona lista")
    st.dataframe(edited[[c for c in cols if c in edited.columns]].sort_values("Wynik /100", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("Pobierz ranking CSV", edited.to_csv(index=False).encode("utf-8"), file_name=f"ranking_akcji_{datetime.now():%Y%m%d}.csv", mime="text/csv")
    st.info("Wynik jest filtrem do dalszej analizy. Zweryfikuj raporty, rozwodnienie akcji, zadłużenie, konkurencję i wycenę scenariuszową.")

with st.expander("Jak interpretować wynik i ograniczenia"):
    st.markdown("""
- **Rewizje prognoz:** ręczna ocena 0–5 na podstawie zmian konsensusu EPS/przychodów w ostatnich 30–90 dniach.
- **Growth:** wzrost przychodów i zysków z Yahoo Finance.
- **Momentum:** zwrot 6M i 12M oraz cena względem 200-dniowej średniej.
- **Quality:** uproszczona ocena ROE, marży operacyjnej i zadłużenia; progi nie są uniwersalne dla branż.
- **Wycena:** forward P/E i PEG; słabe dla spółek nierentownych.
- **FCF:** ostatnia dostępna wartość wolnych przepływów pieniężnych.
- Brak danych nie oznacza dobrego wyniku. Dane Yahoo Finance mogą być opóźnione lub niepełne.
- To nie jest pełny backtest point-in-time ani rekomendacja kupna.
    """)

st.caption("Wersja 1.0 • pobiera publiczne dane rynkowe przez Yahoo Finance. Nie wprowadzaj danych wrażliwych.")
