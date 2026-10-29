import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date

st.set_page_config(page_title="Northstar | Investment Research", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp { background: radial-gradient(ellipse at 15% 0%, #142334 0%, #0b111a 42%, #090e15 100%); color:#e8edf5; }
[data-testid="stSidebar"] { background:#0c131d; border-right:1px solid #202c3c; }
.block-container { padding-top:1.6rem; max-width:1500px; }
h1,h2,h3 { letter-spacing:-0.035em; }
h1 { font-size:2.45rem !important; font-weight:720 !important; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#131f2c,#0f1722); border:1px solid #263649; padding:16px 18px; border-radius:14px; }
[data-testid="stMetricLabel"] { color:#93a4ba; }
[data-testid="stMetricValue"] { color:#e8f1fb; }
.stButton button[kind="primary"] { background:#8de0c0; color:#07130f; border:0; font-weight:700; }
.stButton button { border-radius:9px; }
div[data-testid="stDataFrame"], div[data-testid="stTable"] { border:1px solid #263246; border-radius:10px; overflow:hidden; }
hr { border-color:#263246; }
.northstar-label { color:#8de0c0; letter-spacing:.18em; font-size:.72rem; font-weight:800; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="northstar-label">NORTHSTAR / SYSTEMATIC EQUITY RESEARCH</div>', unsafe_allow_html=True)
st.title("Investment Research Terminal")
st.caption("Systematyczna selekcja spółek • analiza fundamentalna • wycena scenariuszowa • dziennik decyzji")
st.warning("Narzędzie badawcze, nie automatyczna rekomendacja. Dane Yahoo Finance bywają niepełne/opóźnione; wynik modelu nie przewiduje przyszłych stóp zwrotu. Zweryfikuj raporty źródłowe przed transakcją.")

WEIGHTS = {"Wzrost": 22, "Jakość": 22, "Momentum": 17, "Wycena": 22, "Bilans i cash flow": 17, "Rewizje / katalizatory": 0}
DEFAULT_TICKERS = "NVDA, META, GOOGL, AMZN, MSFT, AVGO, TSM, MELI, PLTR, SHOP, LLY, NFLX, UBER, JPM, COST"

for key, default in {
    "screen_results": pd.DataFrame(), "company_data": None,
    "portfolio": pd.DataFrame(columns=["Ticker","Nazwa","Ilość","Średnia cena zakupu","Waluta","Data zakupu","Teza / powód posiadania"]),
    "journal": pd.DataFrame(columns=["Data","Ticker","Decyzja","Horyzont","Teza","Ryzyka","Warunek unieważnienia"]),
    "notes": {},
}.items():
    if key not in st.session_state: st.session_state[key] = default

def num(x):
    try:
        if x is None: return np.nan
        y = float(x)
        return y if np.isfinite(y) else np.nan
    except (TypeError, ValueError): return np.nan

def fmt_money(x, currency="USD"):
    return "n/d" if pd.isna(x) else f"{x:,.2f} {currency}"

def pct(x): return "n/d" if pd.isna(x) else f"{x:.1%}"

def score_growth(rev, eps):
    vals=[]
    for v,cuts in [(rev,[-.05,0,.08,.20,.35]),(eps,[-.10,0,.08,.20,.40])]:
        if pd.notna(v): vals.append(sum(v>=c for c in cuts))
    return int(round(np.mean(vals))) if vals else np.nan

def score_quality(roe,margin,debt):
    vals=[]
    if pd.notna(roe): vals.append(5 if roe>=.25 else 4 if roe>=.15 else 3 if roe>=.08 else 2 if roe>=0 else 0)
    if pd.notna(margin): vals.append(5 if margin>=.30 else 4 if margin>=.20 else 3 if margin>=.10 else 2 if margin>=0 else 0)
    if pd.notna(debt): vals.append(5 if debt<=30 else 4 if debt<=70 else 3 if debt<=120 else 1)
    return int(round(np.mean(vals))) if vals else np.nan

def score_value(pe,peg,fcf_yield):
    if pd.notna(fcf_yield) and fcf_yield>.08: return 5
    if pd.notna(peg) and peg>0: return 5 if peg<.8 else 4 if peg<1.2 else 3 if peg<1.8 else 2 if peg<2.8 else 1
    if pd.notna(pe) and pe>0: return 5 if pe<12 else 4 if pe<18 else 3 if pe<25 else 2 if pe<35 else 1
    return np.nan

def analyze(ticker):
    try:
        obj=yf.Ticker(ticker); info=obj.get_info(); hist=obj.history(period="5y",auto_adjust=True)
        if hist.empty: return {"Ticker":ticker,"Status":"Brak danych"}
        close=hist["Close"].dropna(); price=num(close.iloc[-1])
        ret3=price/num(close.iloc[-min(63,len(close))])-1 if len(close)>20 else np.nan
        ret6=price/num(close.iloc[-min(126,len(close))])-1 if len(close)>20 else np.nan
        ret12=price/num(close.iloc[-min(252,len(close))])-1 if len(close)>20 else np.nan
        ret36=price/num(close.iloc[-min(756,len(close))])-1 if len(close)>30 else np.nan
        ma50=num(close.tail(50).mean()) if len(close)>=50 else np.nan
        ma200=num(close.tail(200).mean()) if len(close)>=200 else np.nan
        above200=bool(price>ma200) if pd.notna(ma200) else False
        cap=num(info.get("marketCap")); avg_vol=num(info.get("averageDailyVolume10Day") or info.get("averageVolume"))
        dollar_vol=price*avg_vol if pd.notna(avg_vol) else np.nan
        revenue=num(info.get("revenueGrowth")); earnings=num(info.get("earningsGrowth")); fcf=num(info.get("freeCashflow"))
        pe=num(info.get("forwardPE")); trailing_pe=num(info.get("trailingPE")); peg=num(info.get("pegRatio"))
        roe=num(info.get("returnOnEquity")); margin=num(info.get("operatingMargins")); debt=num(info.get("debtToEquity"))
        gross_margin=num(info.get("grossMargins")); current_ratio=num(info.get("currentRatio")); beta=num(info.get("beta"))
        fcf_yield=fcf/cap if pd.notna(fcf) and pd.notna(cap) and cap>0 else np.nan
        growth_s=score_growth(revenue,earnings); quality_s=score_quality(roe,margin,debt)
        momentum_s=min(5,round(((ret6>0 if pd.notna(ret6) else False)+(ret12>0 if pd.notna(ret12) else False)+above200+(price>ma50 if pd.notna(ma50) else False))*1.25))
        value_s=score_value(pe,peg,fcf_yield)
        balance_parts=[]
        if pd.notna(fcf): balance_parts.append(5 if fcf>0 else 1)
        if pd.notna(current_ratio): balance_parts.append(5 if current_ratio>=2 else 4 if current_ratio>=1.5 else 3 if current_ratio>=1 else 1)
        if pd.notna(gross_margin): balance_parts.append(5 if gross_margin>=.60 else 4 if gross_margin>=.40 else 3 if gross_margin>=.25 else 2 if gross_margin>=.10 else 1)
        balance_s=int(round(np.mean(balance_parts))) if balance_parts else np.nan
        scores={"Wzrost":growth_s,"Jakość":quality_s,"Momentum":momentum_s,"Wycena":value_s,"Bilans i cash flow":balance_s}
        valid_weight=sum(WEIGHTS[k] for k in scores if pd.notna(scores[k]))
        total=sum((scores[k]/5)*WEIGHTS[k] for k in scores if pd.notna(scores[k]))
        score=round(total,1) if valid_weight>=60 else np.nan
        return {"Ticker":ticker,"Nazwa":info.get("shortName") or info.get("longName") or ticker,"Cena":price,"Waluta":info.get("currency","USD"),
          "Kapitalizacja (mld)":cap/1e9 if pd.notna(cap) else np.nan,"Obrót dzienny (mln)":dollar_vol/1e6 if pd.notna(dollar_vol) else np.nan,
          "Wzrost przychodów r/r":revenue,"Wzrost zysków r/r":earnings,"Zwrot 3M":ret3,"Zwrot 6M":ret6,"Zwrot 12M":ret12,"Zwrot 3Y":ret36,
          "MA50":ma50,"MA200":ma200,"Powyżej MA200":above200,"Forward P/E":pe,"Trailing P/E":trailing_pe,"PEG":peg,
          "ROE":roe,"Marża operacyjna":margin,"Marża brutto":gross_margin,"Dług / kapitał (%)":debt,"Current ratio":current_ratio,
          "FCF (mld)":fcf/1e9 if pd.notna(fcf) else np.nan,"FCF yield":fcf_yield,"Beta":beta,
          "Score wzrost":growth_s,"Score jakość":quality_s,"Score momentum":momentum_s,"Score wycena":value_s,"Score bilans/FCF":balance_s,
          "Wynik systemu /100":score,"Pokrycie czynników (%)":valid_weight,"Status":"OK","_hist":hist,"_info":info}
    except Exception as exc: return {"Ticker":ticker,"Status":f"Błąd pobierania: {str(exc)[:120]}"}

def public_frame(df): return df[[c for c in df.columns if not c.startswith("_")]].copy()

def classify(row):
    score=row.get("Wynik systemu /100",np.nan)
    if pd.isna(score): return "BRAK DANYCH"
    if score>=75 and row.get("Powyżej MA200",False): return "LISTA BADAWCZA"
    if score>=60: return "OBSERWUJ"
    return "NISKI PRIORYTET"

def calculate_fair_value(price,eps,growth,pe_exit,years,margin_safety):
    if any(pd.isna(x) for x in [price,eps,growth,pe_exit]) or price<=0 or eps<=0: return np.nan,np.nan
    fair=eps*((1+growth)**years)*pe_exit
    return fair,fair*(1-margin_safety)

with st.sidebar:
    st.markdown("### SYSTEM SETTINGS")
    min_cap=st.number_input("Min. kapitalizacja (mld, waluta lokalna)",min_value=0.0,value=0.5,step=0.5)
    min_liquidity=st.number_input("Min. obrót dzienny (mln, waluta lokalna)",min_value=0.0,value=1.0,step=1.0)
    min_score=st.slider("Próg wyniku systemu",0,100,65,5)
    st.divider(); st.markdown("**Wagi modelu**")
    for k,v in WEIGHTS.items(): st.write(f"{k}: **{v}%**" if k!="Rewizje / katalizatory" else f"{k}: **{v}% (ręczna ocena poza score)**")
    st.caption("Wagi to hipoteza do testowania, nie uniwersalne optimum.")

tabs=st.tabs(["Overview","Screener","Company deep dive","Portfolio","Decision journal","Methodology"])

with tabs[0]:
    st.subheader("Research dashboard")
    st.write("Jedno miejsce do przejścia od szerokiej selekcji do konkretnej tezy inwestycyjnej.")
    p1,p2,p3,p4=st.columns(4)
    p1.metric("Pozycje w portfelu",len(st.session_state.portfolio)); p2.metric("Spółki w ostatnim screenie",len(st.session_state.screen_results))
    p3.metric("Wpisy w dzienniku",len(st.session_state.journal)); p4.metric("Model","Growth × Quality × Value")
    st.divider(); left,right=st.columns([1.2,1])
    with left:
        st.markdown("#### Proces decyzyjny")
        st.markdown("**01 / Universe** — płynność, wielkość i dostępność danych.")
        st.markdown("**02 / Quant screen** — wzrost, jakość, momentum, wycena i bilans.")
        st.markdown("**03 / Deep dive** — scenariusze wartości, ryzyka, katalizatory i teza.")
        st.markdown("**04 / Portfolio fit** — koncentracja, ekspozycja sektorowa i wielkość pozycji.")
        st.markdown("**05 / Review** — zapisana decyzja, warunek unieważnienia i aktualizacja tezy.")
    with right:
        st.markdown("#### Ostatni ranking")
        if not st.session_state.screen_results.empty:
            view=public_frame(st.session_state.screen_results); cols=[c for c in ["Ticker","Nazwa","Wynik systemu /100","Powyżej MA200"] if c in view]
            st.dataframe(view[cols].sort_values("Wynik systemu /100",ascending=False),hide_index=True,use_container_width=True)
        else: st.info("Uruchom Screener, aby zbudować pierwszą listę badawczą.")
    st.caption("System ma pomagać w podejmowaniu lepszych decyzji, nie podejmować je automatycznie.")

with tabs[1]:
    st.subheader("Systematic stock screener")
    st.write("Wpisz tickery ręcznie lub wczytaj własny universe z CSV. Dla rynków zagranicznych używaj symboli Yahoo Finance, np. ASML.AS, NOVO-B.CO, 7203.T — dostępność danych zależy od instrumentu.")
    tickers_raw=st.text_area("Universe / tickery (oddzielone przecinkami)",DEFAULT_TICKERS,height=80,key="universe")
    uploaded=st.file_uploader("Import universe CSV (wymagana kolumna ticker)",type=["csv"],key="universe_upload")
    if uploaded:
        try:
            up=pd.read_csv(uploaded); col=next((c for c in up.columns if c.lower()=="ticker"),None)
            if col: tickers_raw=",".join(up[col].dropna().astype(str).tolist())
            else: st.error("CSV musi zawierać kolumnę ticker.")
        except Exception as exc: st.error(f"Nie udało się odczytać CSV: {exc}")
    tickers=list(dict.fromkeys(t.strip().upper() for t in tickers_raw.replace("\n",",").split(",") if t.strip()))
    sc1,sc2=st.columns([1,3])
    with sc1: run_screen=st.button("Uruchom analizę",type="primary",use_container_width=True)
    with sc2: st.caption(f"{len(tickers)} unikalnych tickerów • pobieranie danych może potrwać, limity dostawcy mogą wpływać na wyniki.")
    if run_screen:
        rows=[]; bar=st.progress(0); status=st.empty()
        for i,ticker in enumerate(tickers):
            status.write(f"Analiza {ticker} — {i+1}/{len(tickers)}"); rows.append(analyze(ticker)); bar.progress((i+1)/max(len(tickers),1))
        st.session_state.screen_results=pd.DataFrame(rows); bar.empty(); status.empty()
    if not st.session_state.screen_results.empty:
        public=public_frame(st.session_state.screen_results)
        if "Wynik systemu /100" in public:
            public["Decyzja systemu"]=public.apply(classify,axis=1)
            public["Filtr kapitalizacji"]=public.get("Kapitalizacja (mld)",pd.Series(index=public.index,dtype=float)).fillna(0)>=min_cap
            public["Filtr płynności"]=public.get("Obrót dzienny (mln)",pd.Series(index=public.index,dtype=float)).fillna(0)>=min_liquidity
            public["Filtry spełnione"]=public["Filtr kapitalizacji"] & public["Filtr płynności"] & (public["Wynik systemu /100"].fillna(0)>=min_score)
        a,b,c,d=st.columns(4)
        a.metric("Przeanalizowane",len(public))
        b.metric("Lista badawcza",int(public["Decyzja systemu"].eq("LISTA BADAWCZA").sum()) if "Decyzja systemu" in public else 0)
        c.metric("Spełnia filtry",int(public["Filtry spełnione"].sum()) if "Filtry spełnione" in public else 0)
        d.metric("Mediana score",f"{public['Wynik systemu /100'].median():.1f}" if public["Wynik systemu /100"].notna().any() else "n/d")
        show_cols=["Ticker","Nazwa","Cena","Waluta","Kapitalizacja (mld)","Wzrost przychodów r/r","Wzrost zysków r/r","Zwrot 6M","Zwrot 12M","Forward P/E","PEG","Wynik systemu /100","Pokrycie czynników (%)","Decyzja systemu","Filtry spełnione","Status"]
        st.dataframe(public[[c for c in show_cols if c in public]].sort_values("Wynik systemu /100",ascending=False,na_position="last"),use_container_width=True,hide_index=True)
        st.download_button("Pobierz ranking CSV",public.to_csv(index=False).encode("utf-8-sig"),file_name=f"northstar_screen_{date.today().isoformat()}.csv",mime="text/csv")
        st.caption("Brak danych obniża pokrycie modelu i może uniemożliwić score. Wagi nie są normalizowane do 100%, aby brakujące czynniki nie tworzyły fałszywie wysokiego wyniku.")
        st.session_state.screen_public=public

with tabs[2]:
    st.subheader("Company deep dive")
    st.write("Karta spółki łączy dane fundamentalne, zachowanie kursu, uproszczoną wycenę i Twoją własną tezę.")
    dc1,dc2=st.columns([1,1])
    with dc1: company_ticker=st.text_input("Ticker do analizy","NVDA",key="deep_ticker").strip().upper()
    with dc2: st.caption("Dla tickerów zagranicznych sprawdź suffix giełdy w Yahoo Finance. Nie każdy instrument z IBKR ma komplet danych w tym źródle.")
    if st.button("Pobierz kartę spółki",type="primary",key="deep_analyze"): st.session_state.company_data=analyze(company_ticker)
    data=st.session_state.company_data
    if data:
        if data.get("Status")!="OK": st.error(data.get("Status","Nie udało się pobrać danych."))
        else:
            info=data.get("_info",{}); hist=data.get("_hist",pd.DataFrame()); score=data.get("Wynik systemu /100",np.nan)
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Cena",fmt_money(data.get("Cena"),data.get("Waluta","USD")))
            m2.metric("Score systemu",f"{score:.1f}/100" if pd.notna(score) else "Niewystarczające dane")
            m3.metric("Wzrost przychodów",pct(data.get("Wzrost przychodów r/r")))
            m4.metric("Forward P/E",f"{data['Forward P/E']:.1f}×" if pd.notna(data.get("Forward P/E")) else "n/d")
            st.markdown(f"### {data.get('Nazwa',company_ticker)} · {company_ticker}")
            st.caption(f"Sektor: {info.get('sector','n/d')} · Branża: {info.get('industry','n/d')} · Kraj: {info.get('country','n/d')} · Źródło: Yahoo Finance")
            chartcol,factcol=st.columns([1.25,1])
            with chartcol:
                st.markdown("#### Kurs — historia do 5 lat")
                if not hist.empty and "Close" in hist: st.line_chart(hist["Close"].dropna(),height=270)
                st.markdown("#### Zachowanie kursu")
                st.dataframe(pd.DataFrame([{"Miara":"Zwrot 3M","Wynik":pct(data.get("Zwrot 3M"))},{"Miara":"Zwrot 6M","Wynik":pct(data.get("Zwrot 6M"))},{"Miara":"Zwrot 12M","Wynik":pct(data.get("Zwrot 12M"))},{"Miara":"Zwrot 3Y","Wynik":pct(data.get("Zwrot 3Y"))},{"Miara":"Cena vs MA200","Wynik":"Powyżej" if data.get("Powyżej MA200") else "Poniżej / brak danych"}]),hide_index=True,use_container_width=True)
            with factcol:
                st.markdown("#### Fundamenty")
                facts=[("Kapitalizacja",f"{data['Kapitalizacja (mld)']:.2f} mld {data.get('Waluta','')}" if pd.notna(data.get("Kapitalizacja (mld)")) else "n/d"),("Marża brutto",pct(data.get("Marża brutto"))),("Marża operacyjna",pct(data.get("Marża operacyjna"))),("ROE",pct(data.get("ROE"))),("Wzrost zysków r/r",pct(data.get("Wzrost zysków r/r"))),("Trailing P/E",f"{data['Trailing P/E']:.1f}×" if pd.notna(data.get("Trailing P/E")) else "n/d"),("PEG",f"{data['PEG']:.2f}" if pd.notna(data.get("PEG")) else "n/d"),("FCF yield",pct(data.get("FCF yield"))),("Dług / kapitał",f"{data['Dług / kapitał (%)']:.1f}" if pd.notna(data.get("Dług / kapitał (%)")) else "n/d"),("Beta",f"{data['Beta']:.2f}" if pd.notna(data.get("Beta")) else "n/d")]
                st.dataframe(pd.DataFrame(facts,columns=["Metryka","Wartość"]),hide_index=True,use_container_width=True)
            st.markdown("#### Wynik modelu — czynniki")
            factor_rows=[]
            for label,col in [("Wzrost","Score wzrost"),("Jakość","Score jakość"),("Momentum","Score momentum"),("Wycena","Score wycena"),("Bilans i cash flow","Score bilans/FCF")]:
                factor_rows.append({"Czynnik":label,"Ocena 0–5":data.get(col,np.nan),"Waga modelu":f"{WEIGHTS[label]}%"})
            st.dataframe(pd.DataFrame(factor_rows),hide_index=True,use_container_width=True)
            st.markdown("#### Wycena scenariuszowa (nie prognoza)")
            eps_now=num(info.get("trailingEps"))
            if pd.isna(eps_now): eps_now=num(info.get("forwardEps"))
            vc1,vc2,vc3,vc4=st.columns(4)
            with vc1: growth_assumption=st.slider("Wzrost EPS rocznie",-20,50,15,key="fv_growth")/100
            with vc2: exit_pe=st.slider("P/E na końcu okresu",5,60,25,key="fv_pe")
            with vc3: years=st.slider("Lata",1,10,5,key="fv_years")
            with vc4: mos=st.slider("Margines bezpieczeństwa",0,60,25,key="fv_mos")/100
            fair,entry=calculate_fair_value(data.get("Cena",np.nan),eps_now,growth_assumption,exit_pe,years,mos)
            if pd.notna(fair):
                f1,f2,f3=st.columns(3); f1.metric("Wartość w scenariuszu",fmt_money(fair,data.get("Waluta","USD")))
                f2.metric("Potencjalny zwrot do wartości",pct(fair/data["Cena"]-1)); f3.metric("Cena z marginesem bezpieczeństwa",fmt_money(entry,data.get("Waluta","USD")))
                st.caption("Model EPS × końcowy P/E pomija dywidendy, zmianę liczby akcji, cykliczność i niepewność ścieżki wyników. Używaj kilku scenariuszy, nie jednego punktu.")
            else: st.info("Brak dodatniego EPS do prostego modelu P/E. Dla spółek stratnych potrzebny jest osobny model (np. EV/Sales, marża docelowa i rozwodnienie).")
            st.markdown("#### Twoja decyzja")
            existing=st.session_state.notes.get(company_ticker,{})
            verdict_options=["Do dalszej analizy","Chcę kupić / akumulować","Trzymać","Nie kupować","Sprzedać / zamknąć","Obserwować"]
            verdict=st.selectbox("Czy warto mieć tę spółkę?",verdict_options,index=verdict_options.index(existing.get("verdict","Do dalszej analizy")) if existing.get("verdict","Do dalszej analizy") in verdict_options else 0,key=f"verdict_{company_ticker}")
            thesis=st.text_area("Teza inwestycyjna — dlaczego ta spółka ma wygrać?",existing.get("thesis",""),height=100,key=f"thesis_{company_ticker}")
            risks=st.text_area("Najważniejsze ryzyka / co rynek może wyceniać źle?",existing.get("risks",""),height=80,key=f"risks_{company_ticker}")
            invalidation=st.text_input("Co unieważni tezę?",existing.get("invalidation",""),key=f"invalidation_{company_ticker}")
            target_price=st.number_input("Własna cena docelowa (w walucie notowania)",min_value=0.0,value=float(existing.get("target",0) or 0),step=1.0,key=f"target_{company_ticker}")
            if st.button("Zapisz tezę / decyzję",key=f"save_note_{company_ticker}"):
                st.session_state.notes[company_ticker]={"Ticker":company_ticker,"Nazwa":data.get("Nazwa",company_ticker),"Data":date.today().isoformat(),"verdict":verdict,"thesis":thesis,"risks":risks,"invalidation":invalidation,"target":target_price,"score":score}
                st.success("Zapisano w bieżącej sesji. Pobierz dziennik / eksport, aby zachować kopię poza aplikacją.")
            if st.session_state.notes:
                notes_df=pd.DataFrame(list(st.session_state.notes.values()))
                st.download_button("Eksportuj tezy i decyzje CSV",notes_df.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_theses.csv",mime="text/csv")

with tabs[3]:
    st.subheader("Portfolio tracker")
    st.write("Ręcznie zapisuj pozycje, cenę zakupu i własną tezę. To tracker badawczy — nie synchronizuje się automatycznie z IBKR.")
    with st.expander("Dodaj pozycję",expanded=True):
        pc1,pc2,pc3,pc4=st.columns(4)
        with pc1: pticker=st.text_input("Ticker","MSFT",key="p_ticker").strip().upper()
        with pc2: pqty=st.number_input("Liczba akcji",min_value=0.0,value=1.0,step=1.0,key="p_qty")
        with pc3: pcost=st.number_input("Średnia cena zakupu",min_value=0.0,value=100.0,step=1.0,key="p_cost")
        with pc4: pcurrency=st.selectbox("Waluta",["USD","EUR","GBP","PLN","CHF","JPY","DKK","SEK","CAD","AUD"],key="p_currency")
        pdate=st.date_input("Data zakupu",value=date.today(),key="p_date")
        pthesis=st.text_input("Krótka teza / powód posiadania",key="p_thesis")
        if st.button("Dodaj do portfela",type="primary",key="add_position"):
            row={"Ticker":pticker,"Nazwa":pticker,"Ilość":pqty,"Średnia cena zakupu":pcost,"Waluta":pcurrency,"Data zakupu":pdate.isoformat(),"Teza / powód posiadania":pthesis}
            if pticker: st.session_state.portfolio=pd.concat([st.session_state.portfolio,pd.DataFrame([row])],ignore_index=True); st.success(f"Dodano {pticker}.")
    pfile=st.file_uploader("Przywróć portfel z wcześniejszego eksportu CSV",type=["csv"],key="portfolio_upload")
    if pfile:
        try:
            restored=pd.read_csv(pfile); required={"Ticker","Ilość","Średnia cena zakupu","Waluta"}
            if required.issubset(restored.columns): st.session_state.portfolio=restored; st.success("Wczytano portfel z pliku.")
            else: st.error("Plik nie zawiera wymaganych kolumn.")
        except Exception as exc: st.error(f"Błąd importu: {exc}")
    pf=st.session_state.portfolio.copy()
    if not pf.empty:
        if st.button("Odśwież ceny rynkowe i P/L",key="refresh_portfolio_prices"):
            market_prices=[]
            progress=st.progress(0)
            for idx, ticker in enumerate(pf["Ticker"].astype(str).tolist()):
                try:
                    quote=yf.Ticker(ticker).history(period="5d",auto_adjust=True)
                    market_prices.append(float(quote["Close"].dropna().iloc[-1]) if not quote.empty else np.nan)
                except Exception:
                    market_prices.append(np.nan)
                progress.progress((idx+1)/max(len(pf),1))
            pf["Cena rynkowa"]=market_prices
            pf["Wartość rynkowa"]=pd.to_numeric(pf["Ilość"],errors="coerce")*pf["Cena rynkowa"]
            pf["P/L niezrealizowany"]=pf["Wartość rynkowa"]-pd.to_numeric(pf["Ilość"],errors="coerce")*pd.to_numeric(pf["Średnia cena zakupu"],errors="coerce")
            pf["P/L %"]=pf["P/L niezrealizowany"]/(pd.to_numeric(pf["Ilość"],errors="coerce")*pd.to_numeric(pf["Średnia cena zakupu"],errors="coerce")).replace(0,np.nan)
            st.session_state.portfolio=pf
            progress.empty()
            st.rerun()
        pf["Koszt pozycji"]=pd.to_numeric(pf["Ilość"],errors="coerce")*pd.to_numeric(pf["Średnia cena zakupu"],errors="coerce")
        totals=pf.groupby("Waluta")["Koszt pozycji"].sum()
        a,b=st.columns(2); a.metric("Liczba pozycji",len(pf)); b.metric("Liczba unikalnych tickerów",pf["Ticker"].nunique())
        st.dataframe(pf,use_container_width=True,hide_index=True)
        st.markdown("**Koszt zakupu według waluty**")
        st.dataframe(totals.rename("Koszt pozycji").reset_index(),hide_index=True,use_container_width=True)
        st.download_button("Eksportuj portfel CSV",pf.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_portfolio.csv",mime="text/csv")
        remove_ticker=st.selectbox("Usuń wszystkie wiersze dla tickera",["— wybierz —"]+sorted(pf["Ticker"].dropna().unique().tolist()),key="remove_ticker")
        if st.button("Usuń wybrany ticker",key="remove_position") and remove_ticker!="— wybierz —":
            st.session_state.portfolio=st.session_state.portfolio[st.session_state.portfolio["Ticker"]!=remove_ticker].reset_index(drop=True); st.rerun()
    else: st.info("Portfel jest pusty. Dodaj pierwszą pozycję albo wczytaj poprzedni plik CSV.")
    st.caption("Wersja startowa przechowuje dane w pamięci sesji. Po restarcie aplikacji przywróć je z CSV. Trwałą bazę danych i synchronizację IBKR można dodać jako kolejny etap.")

with tabs[4]:
    st.subheader("Decision journal")
    st.write("Zapisuj decyzje przed transakcją — zwłaszcza ryzyko, horyzont i warunek unieważnienia tezy.")
    with st.form("journal_form",clear_on_submit=True):
        jc1,jc2,jc3=st.columns(3)
        with jc1: jticker=st.text_input("Ticker",key="j_ticker").strip().upper()
        with jc2: jdecision=st.selectbox("Decyzja",["Analizuję","Kupuję","Dokupuję","Trzymam","Redukuję","Sprzedaję","Odrzucam"],key="j_decision")
        with jc3: jhorizon=st.selectbox("Horyzont",["< 1 rok","1–3 lata","3–5 lat","5–10 lat","10+ lat"],index=4,key="j_horizon")
        jthesis=st.text_area("Teza / powód decyzji",key="j_thesis"); jrisks=st.text_area("Ryzyka, które akceptuję",key="j_risks"); jinvalid=st.text_input("Warunek unieważnienia tezy",key="j_invalidation")
        submit=st.form_submit_button("Zapisz wpis",type="primary")
        if submit and jticker:
            row={"Data":date.today().isoformat(),"Ticker":jticker,"Decyzja":jdecision,"Horyzont":jhorizon,"Teza":jthesis,"Ryzyka":jrisks,"Warunek unieważnienia":jinvalid}
            st.session_state.journal=pd.concat([st.session_state.journal,pd.DataFrame([row])],ignore_index=True); st.success("Wpis dodany.")
    jfile=st.file_uploader("Importuj dziennik CSV",type=["csv"],key="journal_upload")
    if jfile:
        try:
            imported=pd.read_csv(jfile)
            if {"Data","Ticker","Decyzja"}.issubset(imported.columns): st.session_state.journal=imported; st.success("Wczytano dziennik.")
            else: st.error("Nieprawidłowy format dziennika.")
        except Exception as exc: st.error(f"Błąd importu: {exc}")
    journal=st.session_state.journal
    if not journal.empty:
        st.dataframe(journal,use_container_width=True,hide_index=True)
        st.download_button("Eksportuj dziennik CSV",journal.to_csv(index=False).encode("utf-8-sig"),file_name="northstar_decision_journal.csv",mime="text/csv")
    else: st.info("Brak wpisów. Pierwszy zapis utworzy historię decyzji w bieżącej sesji.")

with tabs[5]:
    st.subheader("Methodology & operating rules")
    st.markdown("### Filozofia")
    st.write("Szukamy spółek, w których jakość biznesu i długi runway wzrostu mogą uzasadniać cenę, ale nie ignorujemy wyceny, momentum, bilansu ani ryzyka utraty kapitału. To hybryda growth, quality, value i trend/momentum — nie czysty screening najniższego P/E.")
    st.markdown("### Model scoringowy")
    st.dataframe(pd.DataFrame([{"Czynnik":"Wzrost","Waga":"22%","Co sprawdza":"Dynamika przychodów i zysków r/r"},{"Czynnik":"Jakość","Waga":"22%","Co sprawdza":"ROE, marża operacyjna, zadłużenie"},{"Czynnik":"Momentum","Waga":"17%","Co sprawdza":"Zwroty 6M/12M i położenie względem MA50/MA200"},{"Czynnik":"Wycena","Waga":"22%","Co sprawdza":"Forward P/E, PEG i FCF yield — zależnie od dostępności"},{"Czynnik":"Bilans i cash flow","Waga":"17%","Co sprawdza":"FCF, current ratio i marża brutto"},{"Czynnik":"Rewizje / katalizatory","Waga":"0% (ręcznie)","Co sprawdza":"Notatka jakościowa; brak automatycznego score z powodu braku wiarygodnego źródła"}]),hide_index=True,use_container_width=True)
    st.markdown("### Reguły, których pilnujemy")
    st.markdown("- **Nie mylimy taniości z niedowartościowaniem.** Niska wycena może sygnalizować trwały problem biznesu.\n- **Nie traktujemy jednego score jako werdyktu.** Wynik tworzy kolejkę do analizy.\n- **Sprawdzamy rozwodnienie akcji, SBC, dług, cykliczność i konkurencję.** Nie wszystkie te elementy są poprawnie dostępne w darmowym feedzie.\n- **Wycena ma scenariusze.** W deep dive zmieniaj wzrost, mnożnik końcowy i margines bezpieczeństwa.\n- **Zapisujemy warunek falsyfikacji tezy.** Musi istnieć powód, który skłoni nas do zmiany zdania.\n- **Backtest dopiero po zebraniu danych point-in-time.** Nie deklarujemy skuteczności bez danych bez survivorship bias, kosztów transakcyjnych i testu poza próbą.")
    st.markdown("### Ograniczenia obecnej wersji")
    st.markdown("- Yahoo Finance nie jest pełnym feedem fundamentalnym ani źródłem danych brokera IBKR.\n- Pokrycie tickerów międzynarodowych zależy od symbolu i giełdy; waluty nie są automatycznie przeliczane.\n- Nie ma jeszcze automatycznych rewizji konsensusu EPS, transkryptów earnings, SEC filings, insiderów ani trwałej bazy danych.\n- Portfolio nie jest połączone z rachunkiem IBKR i nie składa zleceń.\n- To narzędzie edukacyjno-analityczne, nie spersonalizowana porada inwestycyjna.")

st.divider()
st.caption(f"NORTHSTAR v2.0 • Last app render: {datetime.now().strftime('%Y-%m-%d %H:%M')} • Research workflow, not investment advice.")
