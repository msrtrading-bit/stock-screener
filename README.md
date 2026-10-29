# NORTHSTAR — Investment Research Terminal

NORTHSTAR is a Streamlit research prototype for long-term equity investing. It combines a stock screener, company research card, simplified valuation scenario, portfolio tracker, and decision journal.

## Run locally

    pip install -r requirements.txt
    streamlit run app.py

## Deploy to Streamlit Community Cloud

1. Open Streamlit Community Cloud and connect this GitHub repository.
2. Select branch main.
3. Set Main file path to app.py.
4. Deploy. Dependencies are in requirements.txt.

## Current modules

- **Dashboard** — portfolio snapshot, recent screening results, and target allocation.
- **Screener** — manually entered ticker universe or CSV import, factor score, coverage indicator, optional preliminary quality gate, filters, and CSV export.
- **Company research** — market data, price history, fundamental metrics, simplified EPS/terminal-P/E valuation scenario, and an editable thesis.
- **Portfolio** — manually tracked holdings, optional market-price refresh, position sizing by risk layer, preliminary concentration/position-limit flags, and CSV import/export. Exposure weights are calculated separately by currency until FX conversion is implemented.
- **Decision journal** — thesis, risks, decision, and invalidation condition.
- **Methodology** — target allocation, initial risk limits, scoring weights, and limitations.

## NORTHSTAR starting allocation

| Layer | Target |
|---|---:|
| Broad equity ETF core | 50% |
| Quality companies | 25% |
| Aggressive growth | 15% |
| Special situations / speculative | 5% |
| Flexible equity sleeve | 5% |

These weights and the scoring model are initial design hypotheses, not a claim of optimality or guaranteed performance. A 100% equity portfolio can lose more than 50% in a severe drawdown.

## Data and limitations

- Market/fundamental data are retrieved through yfinance / Yahoo Finance. Coverage, freshness, and accuracy vary by ticker.
- The factor score is a heuristic ranking aid, not a forecast, investment recommendation, or validated alpha model. Non-positive P/E and PEG values are excluded from valuation scoring instead of being rewarded as cheap; FCF margin is used instead of absolute FCF size in the balance/FCF factor. Analyst estimate revisions (5% of the intended model weight) are not yet connected, so maximum available weighted coverage is currently 95%.
- The valuation widget compares bear/base/bull EPS-growth and terminal-P/E assumptions and shows a simplified price-implied EPS growth check; it is not a full DCF or reverse DCF.
- Portfolio and journal data are held in Streamlit session state in this version. Export CSV backups regularly; session data are not a durable database.
- No broker synchronization, automatic analyst-revision feed, SEC filing pipeline, point-in-time historical database, or validated backtest is included yet.
- No orders are placed by the app.

## Next development stages

1. Persistent database for holdings, theses, and journal.
2. Better sector-aware fundamentals and valuation models.
3. ETF look-through exposure and sector/concentration checks.
4. SEC filings and estimate-revision data sources.
5. Point-in-time backtesting with delisted stocks, dividends, transaction costs, and out-of-sample validation.

NORTHSTAR is a research tool, not financial advice.
