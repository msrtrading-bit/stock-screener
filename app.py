import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date

st.set_page_config(page_title="NORTHSTAR | Investment Research", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {background: radial-gradient(ellipse at 10% 0%, #17283a 0%, #0b111a 48%, #080d13 100%); color:#e8edf5;}
.block-container {padding-top: 1.8rem; max-width: 1500px;}
[data-testid="stMetric"] {background:rgba(255,255,255,.035); border:1px solid rgba(255,255,255,.08); padding:14px 16px; border-radius:12px;}
h1,h2,h3 {letter-spacing:-.035em;}
.ns-eyebrow {color:#87a9c8; text-transform:uppercase; letter-spacing:.16em; font-size:.72rem; font-weight:700;}
.ns-card {background:rgba(255,255,255,.035); border:1px solid rgba(255,255,255,.09); border-radius:14px; padding:18px;}
div[data-testid="stTabs"] button {font-weight:600;}
</style>
""", unsafe_allow_html=True)

WEIGHTS = {"Jakość biznesu":25, "Wzrost":20, "Wycena":25, "Bilans i FCF":15, "Momentum":10, "Rewizje / katalizatory":5}
DEFAULT_TICKERS = "MSFT, AAPL, GOOGL, AMZN, META, NVDA, AVGO, V, MA, COST, BRK-B, JPM, LLY, UNH, SPGI, ORCL, CRM, NFLX, TSM, ASML"
PORTFOLIO_COLUMNS = ["Ticker","Typ","Ilość","Średnia cena zakupu","Waluta","Warstwa ryzyka","Teza inwestycyjna","Data zakupu"]
NOTE_COLUMNS = ["Data","Ticker","Decyzja","Teza","Ryzyka","Warunek unieważnienia","Cena docelowa"]

def init_state():
    defaults = {
        "screen_results": pd.DataFrame(), "company_data": None,
        "portfolio": pd.DataFrame(columns=PORTFOLIO_COLUMNS),
        "journal": pd.DataFrame(columns=NOTE_COLUMNS), "notes": {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def num(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan

def safe_div(a,b):
    a,b = num(a),num(b)
    if pd.isna(a) or pd.isna(b) or b == 0: return np.nan
    return a/b

def pct(x):
    return "n/d" if pd.isna(num(x)) else f"{num(x)*100:.1f}%"

def money(x, currency="USD"):
    return "n/d" if pd.isna(num(x)) else f"{num(x):,.2f} {currency}"

def score_range(value, low, high, reverse=False):
    value = num(value)
    if pd.isna(value): return np.nan
    result = float(np.clip((value-low)/(high-low)*5,0,5))
    return 5-result if reverse else result

def get_info(ticker):
    obj = yf.Ticker(ticker)
    info = obj.get_info() or {}
    hist = obj.history(period="5y", auto_adjust=True)
    return info, hist

@st.cache_data(ttl=1800, show_spinner=False)
def analyze_ticker(ticker):
    try:
        info, hist = get_info(ticker)
        price = num(info.get("currentPrice"))
        if pd.isna(price) and not hist.empty: price = num(hist["Close"].dropna().iloc[-1])
        currency = info.get("currency","USD")
        cap = num(info.get("marketCap"))
        revenue_growth = num(info.get("revenueGrowth"))
        earnings_growth = num(info.get("earningsGrowth"))
        roe = num(info.get("returnOnEquity"))
        op_margin = num(info.get("operatingMargins"))
        gross_margin = num(info.get("grossMargins"))
        debt_equity = num(info.get("debtToEquity"))
        current_ratio = num(info.get("currentRatio"))
        fcf = num(info.get("freeCashflow"))
        fcf_yield = safe_div(fcf,cap)
        forward_pe = num(info.get("forwardPE"))
        trailing_pe = num(info.get("trailingPE"))
        peg = num(info.get("pegRatio"))
        beta = num(info.get("beta"))
        if not hist.empty and len(hist) > 1:
            close = hist["Close"].dropna()
            ret3 = safe_div(close.iloc[-1], close.iloc[-64])-1 if len(close)>=64 else np.nan
            ret6 = safe_div(close.iloc[-1], close.iloc[-127])-1 if len(close)>=127 else np.nan
            ret12 = safe_div(close.iloc[-1], close.iloc[-253])-1 if len(close)>=253 else np.nan
            ret36 = safe_div(close.iloc[-1], close.iloc[-756])-1 if len(close)>=756 else np.nan
            ma50 = num(close.tail(50).mean()) if len(close)>=50 else np.nan
            ma200 = num(close.tail(200).mean()) if len(close)>=200 else np.nan
            above200 = bool(price > ma200) if pd.notna(price) and pd.notna(ma200) else None
        else:
            ret3=ret6=ret12=ret36=ma50=ma200=np.nan
            above200=None
        # Sector-aware model remains a research heuristic; missing data never earns points.
        quality_parts = [score_range(roe,0.05,0.25), score_range(op_margin,0.05,0.30), score_range(gross_margin,0.20,0.70)]
        growth_parts = [score_range(revenue_growth,0.00,0.25), score_range(earnings_growth,-0.10,0.30)]
        value_parts = [score_range(forward_pe,10,35,True), score_range(peg,0.8,3.0,True), score_range(fcf_yield,0.00,0.08)]
        balance_parts = [score_range(debt_equity,0,200,True), score_range(current_ratio,0.8,2.5), score_range(fcf,0,5e9)]
        momentum_parts = [score_range(ret6,-0.30,0.40), score_range(ret12,-0.40,0.60)]
        factor_data = {
            "Jakość biznesu": (quality_parts, WEIGHTS["Jakość biznesu"]),
            "Wzrost": (growth_parts, WEIGHTS["Wzrost"]),
            "Wycena": (value_parts, WEIGHTS["Wycena"]),
            "Bilans i FCF": (balance_parts, WEIGHTS["Bilans i FCF"]),
            "Momentum": (momentum_parts, WEIGHTS["Momentum"])
        }
        factors = {}
        for name,(parts,weight) in factor_data.items():
            valid = [x for x in parts if pd.notna(x)]
            factors[name] = float(np.mean(valid)) if valid else np.nan
        available_weight = sum(WEIGHTS[k] for k,v in factors.items() if pd.notna(v))
        score = sum((v/5)*WEIGHTS[k] for k,v in factors.items() if pd.notna(v))
        # Do not normalize incomplete scores up to 100. Require at least 60% weighted coverage.
        score = round(score,1) if available_weight >= 60 else np.nan
        dollar_volume = np.nan
        if not hist.empty and "Volume" in hist and pd.notna(price):
            dollar_volume = num((hist["Volume"].dropna().tail(20)*hist["Close"].dropna().tail(20)).mean())
        result = {
            "Ticker":ticker,"Nazwa":info.get("shortName") or info.get("longName") or ticker,
            "Cena":price,"Waluta":currency,"Kapitalizacja (mld)":cap/1e9 if pd.notna(cap) else np.nan,
            "Obrót dzienny (mln)":dollar_volume/1e6 if pd.notna(dollar_volume) else np.nan,
            "Sektor":info.get("sector","n/d"),"Branża":info.get("industry","n/d"),
            "Wzrost przychodów r/r":revenue_growth,"Wzrost zysków r/r":earnings_growth,
            "Zwrot 3M":ret3,"Zwrot 6M":ret6,"Zwrot 12M":ret12,"Zwrot 3Y":ret36,
            "MA50":ma50,"MA200":ma200,"Powyżej MA200":above200,
            "Forward P/E":forward_pe,"Trailing P/E":trailing_pe,"PEG":peg,
            "ROE":roe,"Marża operacyjna":op_margin,"Marża brutto":gross_margin,
            "Dług / kapitał (%)":debt_equity,"Current ratio":current_ratio,
            "FCF (mld)":fcf/1e9 if pd.notna(fcf) else np.nan,"FCF yield":fcf_yield,"Beta":beta,
            "Score jakość":factors["Jakość biznesu"],"Score wzrost":factors["Wzrost"],
            "Score wycena":factors["Wycena"],"Score bilans/FCF":factors["Bilans i FCF"],
            "Score momentum":factors["Momentum"],"Wynik systemu /100":score,
            "Pokrycie czynników (%)":available_weight,"Status":"OK",
            "_info":info,"_hist":hist
        }
        return result
    except Exception as exc:
        return {"Ticker":ticker,"Status":f"Błąd pobierania: {str(exc)[:160]}"}

def public_frame(df):
    return df[[c for c in df.columns if not c.startswith("_")]].copy()

def decision(row):
    score = num(row.get("Wynik systemu /100"))
    if pd.isna(score): return "BRAK DANYCH"
    if score>=75: return "LISTA BADAWCZA"
    if score>=60: return "OBSERWUJ"
    return "NISKI PRIORYTET"

def valuation_scenario(eps, growth, exit_pe, years, margin_safety):
    eps,growth,exit_pe,years,margin_safety = num(eps),num(growth),num(exit_pe),num(years),num(margin_safety)
    if any(pd.isna(x) for x in [eps,growth,exit_pe,years,margin_safety]) or eps<=0 or growth<=-1 or exit_pe<=0:
        return np.nan,np.nan
    future_value = eps*((1+growth)**years)*exit_pe
    return future_value, future_value*(1-margin_safety)

init_state()
st.markdown('<div class="ns-eyebrow">Long-term equity research system</div>', unsafe_allow_html=True)
st.title("NORTHSTAR")
st.caption("Systematyczna selekcja, wycena i kontrola portfela • Horyzont 10–30+ lat")
with st.sidebar:
    st.markdown("## NORTHSTAR")
    st.caption("GARP · US equities · long-term")
    min_cap = st.number_input("Min. kapitalizacja (mld USD)", min_value=0.0, value=2.0, step=1.0)
    min_liquidity = st.number_input("Min. obrót dzienny (mln)", min_value=0.0, value=10.0, step=5.0)
    min_score = st.slider("Minimalny wynik screenera",0,100,65,5)
    st.divider()
    st.markdown("**Wagi modelu**")
    for name,weight in WEIGHTS.items(): st.write(f"{name}: **{weight}%**")
    st.caption("Wynik jest heurystyką badawczą, nie prognozą ani rekomendacją.")

tabs = st.tabs(["Dashboard","Screener","Company research","Portfolio","Decision journal","Metodologia"])

with tabs[0]:
    st.markdown("### Investment overview")
    p = st.session_state.portfolio
    r = st.session_state.screen_results
    n = st.session_state.journal
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pozycje w portfelu",len(p))
    c2.metric("Ostatni screening",len(r))
    c3.metric("Wpisy w dzienniku",len(n))
    c4.metric("Horyzont","10–30+ lat")
    st.divider()
    left,right = st.columns([1.2,1])
    with left:
        st.markdown("#### Architektura portfela")
        alloc = pd.DataFrame([
            {"Warstwa":"Rdzeń indeksowy","Cel %":50,"Rola":"Szeroki rynek i dywersyfikacja"},
            {"Warstwa":"Spółki jakościowe","Cel %":25,"Rola":"Trwała przewaga, FCF i rentowność"},
            {"Warstwa":"Agresywny wzrost","Cel %":15,"Rola":"Wyższy potencjał i wyższa niepewność"},
            {"Warstwa":"Inwestycje specjalne","Cel %":5,"Rola":"Ograniczone zakłady wysokiego ryzyka"},
            {"Warstwa":"Elastyczna część akcyjna","Cel %":5,"Rola":"Dodatkowe okazje lub szeroki ETF"}
        ])
        st.dataframe(alloc,use_container_width=True,hide_index=True)
        st.caption("Docelowa alokacja to punkt startowy. Całość pozostaje portfelem akcyjnym i może doświadczyć obsunięć większych niż 50%.")
    with right:
        st.markdown("#### Ostatni ranking")
        if not r.empty and "Wynik systemu /100" in r:
            cols = [x for x in ["Ticker","Nazwa","Wynik systemu /100","Pokrycie czynników (%)"] if x in r]
            st.dataframe(public_frame(r).sort_values("Wynik systemu /100",ascending=False,na_position="last")[cols],use_container_width=True,hide_index=True)
        else:
            st.info("Uruchom screening, aby zbudować pierwszą listę badawczą.")
    st.markdown("#### Proces decyzyjny")
    st.write("01 — Universe → 02 — Fundamenty i jakość danych → 03 — Wycena scenariuszowa → 04 — Dopasowanie do portfela → 05 — Dziennik decyzji i przegląd.")

with tabs[1]:
    st.markdown("### Systematic stock screener")
    st.write("Wpisz tickery oddzielone przecinkami albo wczytaj CSV z kolumną ticker. Przykładowy universe zawiera duże spółki amerykańskie, ale nie jest rekomendacją.")
    raw = st.text_area("Universe tickerów",DEFAULT_TICKERS,height=100,key="universe")
    upload = st.file_uploader("Import universe CSV",type=["csv"],key="universe_upload")
    if upload:
        try:
            uploaded_df = pd.read_csv(upload)
            col = next((x for x in uploaded_df.columns if x.lower()=="ticker"),None)
            if col: raw = ",".join(uploaded_df[col].dropna().astype(str).tolist())
            else: st.error("CSV musi zawierać kolumnę ticker.")
        except Exception as exc: st.error(f"Nie udało się odczytać CSV: {exc}")
    tickers = list(dict.fromkeys(x.strip().upper() for x in raw.replace("\n",",").split(",") if x.strip()))
    a,b = st.columns([1,3])
    with a: run_screen = st.button("Uruchom screening",type="primary",use_container_width=True)
    with b: st.caption(f"{len(tickers)} tickerów • dane pobierane z Yahoo Finance; pokrycie zależy od instrumentu.")
    if run_screen:
        rows=[]
        progress=st.progress(0)
        status=st.empty()
        for i,ticker in enumerate(tickers):
            status.write(f"Analiza {ticker} ({i+1}/{len(tickers)})")
            rows.append(analyze_ticker(ticker))
            progress.progress((i+1)/max(1,len(tickers)))
        st.session_state.screen_results = pd.DataFrame(rows)
        progress.empty(); status.empty()
    if not st.session_state.screen_results.empty:
        df = public_frame(st.session_state.screen_results)
        if "Wynik systemu /100" in df:
            df["Decyzja systemu"] = df.apply(decision,axis=1)
            df["Filtry spełnione"] = (df["Kapitalizacja (mld)"].fillna(0)>=min_cap) & (df["Obrót dzienny (mln)"].fillna(0)>=min_liquidity) & (df["Wynik systemu /100"].fillna(0)>=min_score)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Przeanalizowane",len(df))
        c2.metric("Lista badawcza",int(df["Decyzja systemu"].eq("LISTA BADAWCZA").sum()) if "Decyzja systemu" in df else 0)
        c3.metric("Spełnia filtry",int(df["Filtry spełnione"].sum()) if "Filtry spełnione" in df else 0)
        valid = df["Wynik systemu /100"].dropna() if "Wynik systemu /100" in df else pd.Series(dtype=float)
        c4.metric("Mediana score",f"{valid.median():.1f}" if not valid.empty else "n/d")
        show = ["Ticker","Nazwa","Cena","Waluta","Sektor","Kapitalizacja (mld)","Wzrost przychodów r/r","Wzrost zysków r/r","Zwrot 6M","Zwrot 12M","Forward P/E","PEG","Wynik systemu /100","Pokrycie czynników (%)","Decyzja systemu","Filtry spełnione","Status"]
        shown = df[[x for x in show if x in df]].sort_values("Wynik systemu /100",ascending=False,na_position="last")
        st.dataframe(shown,use_container_width=True,hide_index=True)
        st.download_button("Eksportuj ranking CSV",df.to_csv(index=False).encode("utf-8-sig"),file_name=f"northstar_screen_{date.today().isoformat()}.csv",mime="text/csv")
        st.caption("Wynik nie jest normalizowany do 100 przy brakujących danych. Brak danych nie jest traktowany jako pozytywny sygnał.")

with tabs[2]:
    st.markdown("### Company research")
    col1,col2 = st.columns([1,2])
    with col1: ticker = st.text_input("Ticker", "MSFT",key="research_ticker").strip().upper()
    with col2: st.caption("Karta badawcza: fundamenty, momentum, wycena orientacyjna oraz własna teza.")
    if st.button("Pobierz dane spółki",type="primary",key="research_button"):
        with st.spinner(f"Pobieranie danych dla {ticker}..."):
            st.session_state.company_data = analyze_ticker(ticker)
    data = st.session_state.company_data
    if data:
        if data.get("Status")!="OK":
            st.error(data.get("Status","Nie udało się pobrać danych."))
        else:
            info = data.get("_info",{})
            hist = data.get("_hist",pd.DataFrame())
            st.markdown(f"## {data.get('Nazwa',ticker)} · {ticker}")
            st.caption(f"Sektor: {data.get('Sektor','n/d')} · Branża: {data.get('Branża','n/d')} · Źródło danych: Yahoo Finance")
            a,b,c,d = st.columns(4)
            a.metric("Cena",money(data.get("Cena"),data.get("Waluta","USD")))
            score = num(data.get("Wynik systemu /100"))
            b.metric("NORTHSTAR score",f"{score:.1f}/100" if pd.notna(score) else "Niewystarczające dane")
            c.metric("Wzrost przychodów",pct(data.get("Wzrost przychodów r/r")))
            d.metric("Forward P/E",f"{data['Forward P/E']:.1f}×" if pd.notna(num(data.get("Forward P/E"))) else "n/d")
            chart,facts = st.columns([1.2,1])
            with chart:
                st.markdown("#### Historia kursu")
                if not hist.empty and "Close" in hist: st.line_chart(hist["Close"].dropna(),height=260)
                st.markdown("#### Momentum")
                st.dataframe(pd.DataFrame([
                    {"Miara":"Zwrot 3M","Wartość":pct(data.get("Zwrot 3M"))},
                    {"Miara":"Zwrot 6M","Wartość":pct(data.get("Zwrot 6M"))},
                    {"Miara":"Zwrot 12M","Wartość":pct(data.get("Zwrot 12M"))},
                    {"Miara":"Zwrot 3Y","Wartość":pct(data.get("Zwrot 3Y"))},
                    {"Miara":"Cena vs MA200","Wartość":"Powyżej" if data.get("Powyżej MA200") is True else ("Poniżej" if data.get("Powyżej MA200") is False else "n/d")}
                ]),hide_index=True,use_container_width=True)
            with facts:
                st.markdown("#### Fundamenty")
                rows = [
                    ("Kapitalizacja (mld)",data.get("Kapitalizacja (mld)")),
                    ("ROE",pct(data.get("ROE"))),("Marża brutto",pct(data.get("Marża brutto"))),
                    ("Marża operacyjna",pct(data.get("Marża operacyjna"))),
                    ("Wzrost zysków",pct(data.get("Wzrost zysków r/r"))),
                    ("Trailing P/E",f"{data['Trailing P/E']:.1f}×" if pd.notna(num(data.get("Trailing P/E"))) else "n/d"),
                    ("PEG",f"{data['PEG']:.2f}" if pd.notna(num(data.get("PEG"))) else "n/d"),
                    ("FCF yield",pct(data.get("FCF yield"))),
                    ("Dług / kapitał",data.get("Dług / kapitał (%)")),
                    ("Beta",data.get("Beta"))
                ]
                st.dataframe(pd.DataFrame(rows,columns=["Metryka","Wartość"]),hide_index=True,use_container_width=True)
            st.markdown("#### Wycena scenariuszowa")
            eps = num(info.get("trailingEps"))
            if pd.isna(eps): eps = num(info.get("forwardEps"))
            v1,v2,v3,v4 = st.columns(4)
            with v1: growth = st.slider("Wzrost EPS rocznie (%)",-20,50,12,key="val_growth")/100
            with v2: exit_pe = st.slider("Końcowe P/E",5,60,22,key="val_exit_pe")
            with v3: years = st.slider("Horyzont (lata)",1,15,10,key="val_years")
            with v4: mos = st.slider("Margines bezpieczeństwa (%)",0,60,25,key="val_mos")/100
            future,entry = valuation_scenario(eps,growth,exit_pe,years,mos)
            price = num(data.get("Cena"))
            if pd.notna(future) and pd.notna(price) and price>0:
                x,y,z = st.columns(3)
                x.metric("Wartość scenariusza na koniec",money(future,data.get("Waluta","USD")))
                y.metric("Zwrot ceny do wartości",pct(future/price-1))
                z.metric("Cena z marginesem bezpieczeństwa",money(entry,data.get("Waluta","USD")))
                annualized = (future/price)**(1/years)-1 if future>0 else np.nan
                st.metric("Uproszczony annualizowany zwrot do wartości",pct(annualized))
                st.caption("To model EPS × końcowy P/E, nie pełny DCF. Nie uwzględnia w pełni dywidend, zmian liczby akcji, cykliczności ani zmian mnożnika w trakcie okresu. Używaj bear/base/bull i sprawdzaj założenia.")
            else:
                st.info("Brak dodatniego EPS do uproszczonej wyceny P/E. Dla firm stratnych potrzebny jest model EV/Sales, docelowych marż i rozwodnienia.")
            st.markdown("#### Twoja teza i decyzja")
            existing = st.session_state.notes.get(ticker,{})
            verdicts = ["Do dalszej analizy","Chcę kupić / akumulować","Trzymać","Obserwować","Nie kupować","Sprzedać / zamknąć"]
            verdict = st.selectbox("Czy chcesz posiadać tę spółkę?",verdicts,index=verdicts.index(existing.get("Decyzja","Do dalszej analizy")) if existing.get("Decyzja","Do dalszej analizy") in verdicts else 0,key=f"verdict_{ticker}")
            thesis = st.text_area("Dlaczego ta spółka ma wygrywać przez lata?",existing.get("Teza",""),height=100,key=f"thesis_{ticker}")
            risks = st.text_area("Najważniejsze ryzyka",existing.get("Ryzyka",""),height=80,key=f"risks_{ticker}")
            invalidation = st.text_input("Co unieważni tezę?",existing.get("Warunek unieważnienia",""),key=f"invalidation_{ticker}")
            target = st.number_input("Własna cena docelowa",min_value=0.0,value=float(existing.get("Cena docelowa",0) or 0),step=1.0,key=f"target_{ticker}")
            if st.button("Zapisz decyzję",key=f"save_note_{ticker}"):
                st.session_state.notes[ticker] = {"Data":date.today().isoformat(),"Ticker":ticker,"Decyzja":verdict,"Teza":thesis,"Ryzyka":risks,"Warunek unieważnienia":invalidation,"Cena docelowa":target}
                st.success("Zapisano w bieżącej sesji. Wyeksportuj CSV, aby zachować kopię.")
            if st.session_state.notes:
                notes_df = pd.DataFrame(list(st.session_state.notes.values()))
                st.download_button("Eksportuj tezy CSV",notes_df.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_theses.csv",mime="text/csv")

with tabs[3]:
    st.markdown("### Portfolio architect")
    st.warning("Dane portfela w tej wersji są przechowywane w sesji aplikacji. Eksportuj CSV po każdej ważnej zmianie; trwała baza danych będzie osobnym etapem.")
    with st.expander("Dodaj pozycję",expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1: pticker = st.text_input("Ticker / symbol ETF",key="p_ticker").strip().upper()
        with c2: ptype = st.selectbox("Typ",["ETF indeksowy","Spółka jakościowa","Agresywny wzrost","Inwestycja specjalna","Elastyczna część"],key="p_type")
        with c3: qty = st.number_input("Ilość",min_value=0.0,value=1.0,step=1.0,key="p_qty")
        with c4: cost = st.number_input("Średnia cena zakupu",min_value=0.0,value=100.0,step=1.0,key="p_cost")
        c5,c6,c7 = st.columns(3)
        with c5: currency = st.selectbox("Waluta",["USD","EUR","GBP","PLN","CHF","JPY","DKK","SEK","CAD","AUD"],key="p_currency")
        with c6: layer = st.selectbox("Warstwa ryzyka",["Rdzeń indeksowy","Jakościowy wzrost","Agresywny wzrost","Inwestycje specjalne","Elastyczna część"],key="p_layer")
        with c7: purchase_date = st.date_input("Data zakupu",value=date.today(),key="p_date")
        thesis = st.text_input("Teza / powód posiadania",key="p_thesis")
        if st.button("Dodaj do portfela",type="primary",key="add_position"):
            if pticker and qty>0 and cost>0:
                row = {"Ticker":pticker,"Typ":ptype,"Ilość":qty,"Średnia cena zakupu":cost,"Waluta":currency,"Warstwa ryzyka":layer,"Teza inwestycyjna":thesis,"Data zakupu":purchase_date.isoformat()}
                st.session_state.portfolio = pd.concat([st.session_state.portfolio,pd.DataFrame([row])],ignore_index=True)
                st.success(f"Dodano {pticker}.")
            else: st.error("Podaj ticker, dodatnią ilość i cenę zakupu.")
    restore = st.file_uploader("Przywróć portfel z CSV",type=["csv"],key="portfolio_restore")
    if restore:
        try:
            imported = pd.read_csv(restore)
            if {"Ticker","Ilość","Średnia cena zakupu","Waluta"}.issubset(imported.columns):
                st.session_state.portfolio = imported
                st.success("Wczytano portfel.")
            else: st.error("Plik nie zawiera wymaganych kolumn.")
        except Exception as exc: st.error(f"Błąd importu: {exc}")
    pf = st.session_state.portfolio.copy()
    if not pf.empty:
        if st.button("Odśwież ceny i P/L",key="refresh_prices"):
            prices=[]
            progress=st.progress(0)
            for i,t in enumerate(pf["Ticker"].astype(str)):
                try:
                    hist = yf.Ticker(t).history(period="5d",auto_adjust=True)
                    prices.append(float(hist["Close"].dropna().iloc[-1]) if not hist.empty else np.nan)
                except Exception: prices.append(np.nan)
                progress.progress((i+1)/max(1,len(pf)))
            pf["Cena rynkowa"] = prices
            pf["Wartość rynkowa"] = pd.to_numeric(pf["Ilość"],errors="coerce")*pf["Cena rynkowa"]
            pf["Koszt pozycji"] = pd.to_numeric(pf["Ilość"],errors="coerce")*pd.to_numeric(pf["Średnia cena zakupu"],errors="coerce")
            pf["P/L niezrealizowany"] = pf["Wartość rynkowa"]-pf["Koszt pozycji"]
            pf["P/L %"] = pf["P/L niezrealizowany"]/pf["Koszt pozycji"].replace(0,np.nan)
            st.session_state.portfolio = pf
            progress.empty()
            st.rerun()
        pf["Koszt pozycji"] = pd.to_numeric(pf["Ilość"],errors="coerce")*pd.to_numeric(pf["Średnia cena zakupu"],errors="coerce")
        cost_by_currency = pf.groupby("Waluta",dropna=False)["Koszt pozycji"].sum().reset_index()
        c1,c2,c3 = st.columns(3)
        c1.metric("Pozycje",len(pf))
        c2.metric("Unikalne tickery",pf["Ticker"].nunique())
        c3.metric("Waluty",pf["Waluta"].nunique())
        st.dataframe(pf,use_container_width=True,hide_index=True)
        st.markdown("#### Koszt według waluty (bez automatycznego FX)")
        st.dataframe(cost_by_currency,use_container_width=True,hide_index=True)
        st.download_button("Eksportuj portfel CSV",pf.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_portfolio.csv",mime="text/csv")
        remove = st.selectbox("Ticker do usunięcia",["— wybierz —"]+sorted(pf["Ticker"].dropna().astype(str).unique().tolist()),key="remove_ticker")
        if st.button("Usuń wszystkie pozycje tickera",key="remove_position") and remove!="— wybierz —":
            st.session_state.portfolio = pf[pf["Ticker"]!=remove].reset_index(drop=True)
            st.rerun()
        if "Warstwa ryzyka" in pf:
            st.markdown("#### Alokacja według warstwy ryzyka — koszt zakupu")
            st.dataframe(pf.groupby("Warstwa ryzyka",dropna=False)["Koszt pozycji"].sum().reset_index(),use_container_width=True,hide_index=True)
    else:
        st.info("Portfel jest pusty. Dodaj pozycję lub wczytaj poprzedni eksport CSV.")

with tabs[4]:
    st.markdown("### Decision journal")
    with st.form("journal_form",clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: jticker = st.text_input("Ticker").strip().upper()
        with c2: jdecision = st.selectbox("Decyzja",["Analizuję","Kupuję","Dokupuję","Trzymam","Redukuję","Sprzedaję","Odrzucam"])
        with c3: jhorizon = st.selectbox("Horyzont",["1–3 lata","3–5 lat","5–10 lat","10+ lat"],index=3)
        jthesis = st.text_area("Teza / powód decyzji")
        jrisks = st.text_area("Ryzyka, które akceptuję")
        jinvalid = st.text_input("Warunek unieważnienia tezy")
        submitted = st.form_submit_button("Zapisz wpis",type="primary")
        if submitted and jticker:
            row = {"Data":date.today().isoformat(),"Ticker":jticker,"Decyzja":jdecision,"Teza":jthesis,"Ryzyka":jrisks,"Warunek unieważnienia":jinvalid,"Cena docelowa":""}
            st.session_state.journal = pd.concat([st.session_state.journal,pd.DataFrame([row])],ignore_index=True)
            st.success("Wpis dodany.")
        elif submitted: st.error("Podaj ticker.")
    journal_upload = st.file_uploader("Importuj dziennik CSV",type=["csv"],key="journal_upload")
    if journal_upload:
        try:
            imported = pd.read_csv(journal_upload)
            if {"Data","Ticker","Decyzja"}.issubset(imported.columns):
                st.session_state.journal = imported
                st.success("Wczytano dziennik.")
            else: st.error("Nieprawidłowy format dziennika.")
        except Exception as exc: st.error(f"Błąd importu: {exc}")
    journal = st.session_state.journal
    if not journal.empty:
        st.dataframe(journal,use_container_width=True,hide_index=True)
        st.download_button("Eksportuj dziennik CSV",journal.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_decision_journal.csv",mime="text/csv")
    else: st.info("Brak wpisów. Dodaj pierwszą decyzję.")

with tabs[5]:
    st.markdown("### Metodologia i zasady działania")
    st.markdown("#### Docelowa alokacja portfela")
    st.dataframe(pd.DataFrame([
        {"Warstwa":"Rdzeń indeksowy","Cel":"50%","Zasada":"Szeroki ETF na rynek USA lub globalny"},
        {"Warstwa":"Spółki jakościowe","Cel":"25%","Zasada":"Wysoka jakość biznesu i rozsądna wycena"},
        {"Warstwa":"Agresywny wzrost","Cel":"15%","Zasada":"Wyższe ryzyko, mniejsze pozycje"},
        {"Warstwa":"Inwestycje specjalne","Cel":"5%","Zasada":"Każda pozycja maks. 1% portfela"},
        {"Warstwa":"Elastyczna część akcyjna","Cel":"5%","Zasada":"Nie kupuj tylko po to, by wykorzystać gotowy limit"}
    ]),use_container_width=True,hide_index=True)
    st.markdown("#### Limity ryzyka — wartości startowe do testowania")
    st.markdown("- Spółka jakościowa: zwykle 2–4%, limit projektowy 5% całego portfela.\\n- Spółka agresywnego wzrostu: zwykle 1–2,5%, limit 3%.\\n- Inwestycja spekulacyjna: zwykle 0,25–0,5%, limit 1%; cała warstwa maks. 5%.\\n- Orientacyjny limit sektora technologicznego: 30%, uwzględniając ekspozycję przez ETF-y; inny pojedynczy sektor: 20–25%.\\n- Limity muszą uwzględniać nakładające się ekspozycje ETF-ów oraz korelacje biznesowe.")
    st.markdown("#### Wagi scoringu")
    st.dataframe(pd.DataFrame([{"Czynnik":k,"Waga":f"{v}%"} for k,v in WEIGHTS.items()]),use_container_width=True,hide_index=True)
    st.markdown("#### Wycena i dyscyplina")
    st.markdown("- Używaj scenariuszy pesymistycznego, bazowego i optymistycznego; nie traktuj jednej ceny docelowej jako faktu.\\n- DCF dla przewidywalnych przepływów, reverse DCF do analizy oczekiwań zawartych w cenie, wycena porównawcza dobrana do sektora.\\n- Dla firm nierentownych nie wymuszaj P/E; analizuj EV/Sales, docelowe marże, gotówkę i rozwodnienie.\\n- Przegląd danych co kwartał; rebalancing co 6–12 miesięcy lub po istotnym odchyleniu od celu.\\n- Nie sprzedawaj automatycznie tylko dlatego, że kurs spadł. Weryfikuj fundamenty i tezę.\\n- Backtest wymaga danych point-in-time, delistowanych spółek, dywidend, kosztów i testu poza próbą.")
    st.markdown("#### Ograniczenia obecnej wersji")
    st.markdown("- Yahoo Finance to źródło prototypowe: dane mogą być opóźnione, niepełne lub niespójne.\\n- Scoring jest heurystyczny i nie jest backtestowany; nie jest rekomendacją inwestycyjną.\\n- Nie ma jeszcze automatycznego feedu rewizji analityków, SEC filings, trwałej bazy danych ani synchronizacji z brokerem.\\n- Portfel i dziennik w tej wersji działają w pamięci sesji; eksportuj CSV, by zachować dane.\\n- Wycena EPS × końcowe P/E jest uproszczeniem, a nie pełnym modelem DCF.")

st.divider()
st.caption(f"NORTHSTAR v3.0 • Ostatnie renderowanie: {datetime.now().strftime('%Y-%m-%d %H:%M')} • Research tool, not investment advice.")
