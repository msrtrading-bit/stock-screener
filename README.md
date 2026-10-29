# NORTHSTAR — Investment Research Terminal

NORTHSTAR is a dark, minimalist Streamlit research terminal for long-term equity investing. It combines a stock screener, company research card, scenario valuation, portfolio tracker, and decision journal.

## Run locally

    pip install -r requirements.txt
    streamlit run app.py

## Deploy to Streamlit Community Cloud

1. Connect this repository to Streamlit Community Cloud.
2. Select branch main and main file path app.py.
3. Deploy. Theme settings live in .streamlit/config.toml.

## Recommended private setup: persistent storage + password

By default, portfolio/thesis/journal data stays in Streamlit session state. For durable storage across sessions and app restarts, configure a Supabase project.

1. Create a Supabase project.
2. In Supabase SQL Editor, run the script in supabase/schema.sql.
3. In Streamlit Community Cloud, open the app's Settings → Secrets and add the following TOML. Use your project URL and the server-side service_role key from Supabase API settings. Choose a strong, unique password.

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
service_role_key = "YOUR_SERVICE_ROLE_KEY"

[auth]
password = "CHOOSE_A_LONG_UNIQUE_PASSWORD"
```

4. Save secrets and reboot the app. The app will show a login screen and use the database for portfolio, journal, and thesis notes.
5. Never put the service-role key in GitHub, app code, screenshots, or chat. Keep it only in Streamlit Secrets. The app password is a shared single-owner gate, not a full multi-user identity system.

If Supabase secrets are absent, the app runs in session-only mode and warns about the limitation. **Do not enter sensitive portfolio information into a publicly accessible instance before configuring the password gate.** The local .streamlit/secrets.toml file is excluded by .gitignore.

## Current modules

- **Dashboard** — target allocation, latest screening snapshot, portfolio/journal counts.
- **Screener** — ticker universe or CSV import, heuristic factor score, coverage indicator, preliminary quality gate, filters, CSV export.
- **Company research** — price history, fundamental metrics, bear/base/bull EPS-growth and terminal-P/E scenarios, and an editable thesis.
- **Portfolio** — holdings, price refresh, risk-layer limits, preliminary concentration checks, CSV import/export.
- **Decision journal** — thesis, risks, decision, and invalidation condition.
- **Methodology** — target allocation, scoring weights, risk limits, and limitations.

## NORTHSTAR starting allocation

| Layer | Target |
|---|---:|
| Broad equity ETF core | 50% |
| Quality companies | 25% |
| Aggressive growth | 15% |
| Special situations / speculative | 5% |
| Flexible equity sleeve | 5% |

These weights are initial design hypotheses, not a claim of optimality or guaranteed performance. A 100% equity portfolio can lose more than 50% in a severe drawdown.

## Data, methodology, and limitations

- Market/fundamental data are retrieved through yfinance / Yahoo Finance. Coverage, freshness, and accuracy vary by ticker.
- The factor score is a heuristic ranking aid, not a forecast, investment recommendation, or validated alpha model. Non-positive P/E and PEG values are excluded from valuation scoring; FCF margin is used instead of absolute FCF size in the balance/FCF factor.
- Analyst estimate revisions (5% of intended model weight) are not connected, so maximum available weighted coverage is currently 95%.
- Valuation is an EPS × terminal-P/E scenario model, not a full DCF or reverse DCF. The price-implied-growth indicator is a simplified expectation check.
- Portfolio position weights are currently calculated separately by currency; there is no whole-portfolio FX conversion or ETF look-through exposure yet.
- Persistent storage is optional and requires Supabase configuration. Without it, session data are not durable.
- No broker synchronization, automated analyst-revision feed, SEC filing pipeline, point-in-time historical database, or validated backtest is included.
- No orders are placed by the app.

## Next development stages

1. Validate app startup and data handling through CI and the live deployment.
2. Enable Supabase persistence and access password.
3. Add whole-portfolio FX exposure and ETF look-through.
4. Improve valuation methods by sector, including discounted cash flow.
5. Add SEC filings and analyst-estimate revision data.
6. Build a point-in-time backtest with delisted stocks, dividends, transaction costs, and out-of-sample validation.

NORTHSTAR is a research tool, not financial advice.