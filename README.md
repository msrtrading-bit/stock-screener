# Growth + Momentum Stock Screener

Aplikacja Streamlit do wstępnej selekcji akcji według wzrostu, momentum, jakości, wyceny i free cash flow.

## Uruchomienie w Streamlit Community Cloud
- Main file path: `app.py`
- Dependencies are listed in `requirements.txt`.

## Funkcje
- Wpisywanie tickerów lub import CSV (kolumna `ticker`)
- Scoring 0–100 i filtrowanie po kapitalizacji/płynności
- Wzrost przychodów i zysków, momentum 6M/12M, średnia 200-dniowa
- Uproszczone miary jakości, forward P/E, PEG i FCF
- Ręczna ocena rewizji prognoz
- Eksport wyników do CSV

## Ograniczenia
Dane pochodzą z Yahoo Finance przez yfinance i mogą być niepełne, opóźnione lub błędne. Rewizje prognoz są oceniane ręcznie. Scoring jest heurystyką do tworzenia listy do dalszej analizy, a nie rekomendacją inwestycyjną. Aplikacja nie zawiera pełnego backtestu point-in-time ani danych o spółkach wycofanych z rynku.
