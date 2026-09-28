# APIx — historical airfare price index prototype

APIx (Airfare Price Index) is a prototype for turning fare quotes into a transparent, route-weighted price indicator. It uses only the public historical CSV snapshots placed in `data/raw/`; this prototype does not scrape.

## Architecture

```text
Historical CSVs (data/raw; local only)
             |
     inspect_data.py
             |
  loaders -> cleaning -> canonical fare quotes
             |
     build_processed.py -> compact Parquet (data/processed; committed)
             |
     Streamlit dashboard -> route, lead-time, carrier, quality views

DGCA city-pair passenger weights + DGCA fare reference (data/external templates)
```

The deployed app reads only `data/processed/` and `data/external/`; raw CSVs are git-ignored.

## Data sources and assumptions

- EaseMyTrip `Clean_Dataset.csv`: [Kaggle: Flight Price Prediction by shubhambathwal](https://www.kaggle.com/datasets/shubhambathwal/flight-price-prediction). The observed file has 300,153 rows and fields `source_city`, `destination_city`, `airline`, `flight`, `class`, `days_left`, `duration`, `stops`, and `price`. It has no calendar date. This is used for lead-time, route, and carrier analysis only.
- EaseMyTrip `business.csv` and `economy.csv` contain a `date` column, observed from 2022-02-11 through 2022-03-31. [Dataset documentation](https://github.com/MahishaG/Flight-Price-Prediction/blob/main/README.md) describes this as the flight departure date (and separately notes a 50-day collection window), not a quote-collection timestamp. They are not used by the build or dashboard and are unsuitable for time-series price indexing. The source collection window is documented separately as February 11 to March 31, 2022.
- Goibibo file `goibibo_flights_data.csv` contains `flight date` (observed from 2023-06-26 through 2023-08-13), but the file itself does not establish whether this is departure date or quote-collection date. It is retained for route/carrier analysis only and is not used to calculate APIx time series. The source is [Kaggle: Goibibo flight data by iamavyukt](https://www.kaggle.com/datasets/iamavyukt/goibibo-flight-data).
- Check the dataset pages and their linked source terms/licences before reuse or redistribution. No licence terms are asserted here.
- Cities map to IATA codes: Delhi DEL, Mumbai BOM, Bangalore/Bengaluru BLR, Kolkata CCU, Hyderabad HYD, Chennai MAA. Unknown cities are not assigned a route.
- `price` is treated as total fare in INR. There is no supported base/tax split, so `base_fare` and `taxes` stay null.

### Assumptions

- The user-provided raw file names and their contents are the source of truth. Inspection found a 2022 `Clean_Dataset.csv` without dates and separate `business.csv`/`economy.csv` files with a `date` field; the business/economy date values match the stated February–March 2022 window, but the clean dataset itself has no date and no quote-collection date can be inferred from it.
- The EaseMyTrip `date` field is a departure date, not a quote-collection date; Goibibo `flight date` remains unverified. Neither is used as an observation timestamp, so no dated index is produced from these files.
- Goibibo does not provide booking lead time in the observed columns; therefore it cannot populate lead-time cells even though it has a date-like field.

## Methodology

- Cleaning removes exact duplicates, missing/non-positive prices, unparseable routes, and within-cell fare outliers. Groups with at least 20 rows use 1.5×IQR bounds. Smaller groups use median ± 3 scaled median absolute deviations (MAD).
- Lead-time buckets are T+1, T+7, T+15, T+30, and T+45. Each `days_left` is assigned to the nearest bucket only when it is within 2 calendar days; other values are omitted from bucket-based views.
- A potential time-series APIx uses a Jevons elementary aggregate (geometric mean) per route × carrier × cabin × lead-time bucket, divides by each cell’s base fare, then computes a route-weighted geometric mean. Route weights are renormalised over routes present for each date.
- The intended base is the first complete Monday–Sunday week of daily observations. Fixed-base is the default; optional chain-linking compounds adjacent-period movements over shared routes.
- Daily index can be aggregated weekly or monthly as the mean of daily index values. The current supplied data cannot produce a defensible time series: the main EaseMyTrip file has no date; the other EaseMyTrip files have departure dates rather than quote-observation dates; and Goibibo has no confirmed observation timestamp or lead time.
- `route_weights.csv` is an explicitly marked template. Replace passenger counts with sourced DGCA city-pair passenger volumes; resulting weights are normalised to sum to one.

## Limitations

- No calendar dates in EaseMyTrip `Clean_Dataset.csv`; it cannot support time-series inflation measurement.
- Placeholder route weights are not representative weights and are shown with a warning in the app.
- Total fare only; taxes and base fare are not separately observed.
- Supplied 2022/2023 snapshots are historical and not current. The observation window and sampling process limit conclusions.
- The index functions require a full seven-day base week; partial or sparse dates return no index.
- No APIx-to-DGCA backtest is possible until both a confirmed dated APIx series and sourced DGCA reference values exist.

## Run locally

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/inspect_data.py
python scripts/build_processed.py
pytest -q
streamlit run app/streamlit_app.py
```

A clean clone without raw files can still run the dashboard from the committed `data/processed/*.parquet` files. Rebuilding requires the user-provided files in `data/raw/`. `data/raw/` is ignored by Git.

## Deploy on Streamlit Community Cloud

1. Push this repository, including `data/processed/`, to GitHub.
2. Create a Streamlit Community Cloud app for this repository with main file `app/streamlit_app.py`.
3. Streamlit installs `requirements.txt`; no raw data or network access is needed at runtime.
4. Keep the repository's processed data under 25 MB total.

## Future live pipeline

A future approved quote collection service could write timestamped quotes into the canonical schema, then reuse the same validation, cell aggregation, route weights, index, and dashboard. Store an explicit quote-observation timestamp separately from departure date and booking lead time. Any future collector must respect robots.txt, each provider's terms of service, applicable laws, and rate limits. There is no scraping in this prototype.

## DGCA templates and backtest

- `data/external/route_weights.csv`: replace placeholder passengers with authoritative city-pair passenger counts, set `is_placeholder` to `false`, then rerun `python scripts/build_processed.py` (or refresh the app to load the revised weights).
- `data/external/dgca_monthly.csv`: fill `month` (YYYY-MM), `avg_domestic_fare_inr`, `source_url`, and `notes` with sourced observations. The dashboard explains when this file is empty. Once populated, monthly changes can be compared; any available sample is short and exploratory.



