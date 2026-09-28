"""Streamlit dashboard for the processed historical APIx prototype."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import plotly.express as px
import streamlit as st

from apix.backtest import load_dgca
from apix.config import PROCESSED_DIR
from apix.index import lead_time_tables
from apix.weights import load_route_weights

st.set_page_config(page_title="APIx | Airfare Price Index", page_icon="✈️", layout="wide")
st.title("APIx · Airfare Price Index")
st.caption("A historical-data prototype for tracking Indian domestic airfares. No scraping is used.")

@st.cache_data
def available_data() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_parquet(p) for p in sorted(PROCESSED_DIR.glob("*.parquet"))}

@st.cache_data
def quality_report(name: str) -> dict:
    path = PROCESSED_DIR / f"{name}_quality.json"
    return json.loads(path.read_text()) if path.exists() else {}

frames = available_data()
if not frames:
    st.error("No processed datasets found. Add the provided raw CSVs and run `python scripts/build_processed.py`, then commit data/processed/*.parquet.")
    st.stop()

names = list(frames)
labels = {"easemytrip": "EaseMyTrip · lead-time dataset", "goibibo": "Goibibo · dated fares (date meaning unverified)"}
with st.sidebar:
    st.header("Explore")
    dataset = st.selectbox("Dataset", names, format_func=lambda n: labels.get(n, n))
    data = frames[dataset]
    classes = sorted(data.cabin_class.dropna().astype(str).unique())
    cabin = st.selectbox("Cabin class", classes, index=classes.index("Economy") if "Economy" in classes else 0)
    routes = sorted(data.route.dropna().unique())
    selected_routes = st.multiselect("Routes", routes, default=routes)

view = data[data.cabin_class.astype(str).eq(cabin) & data.route.isin(selected_routes)].copy()
try:
    weights = load_route_weights()
except (FileNotFoundError, ValueError):
    weights = pd.DataFrame(columns=["route", "weight", "is_placeholder"])
if weights.get("is_placeholder", pd.Series(dtype=bool)).astype(str).str.lower().eq("true").any():
    st.warning("Route weights are placeholders. Replace data/external/route_weights.csv with DGCA city-pair passenger data and rebuild.")

st.header("1 · Overview")
if dataset == "easemytrip":
    st.info("Clean_Dataset.csv has no calendar date. A time-series index cannot be computed from it; this view reports lead-time and route patterns only.")
    curve, heat, carrier = lead_time_tables(view)
    a, b = st.columns(2)
    a.metric("Fare quotes", f"{len(view):,}")
    b.metric("Routes selected", len(selected_routes))
else:
    st.info("Goibibo provides `flight date`, which appears in the source as a date field but is not documented as quote-collection date. It also has no booking lead-time field. The prototype does not treat this as an observation time or produce an APIx time series.")
    curve, heat, carrier = lead_time_tables(view)
    st.metric("Fare quotes", f"{len(view):,}")

st.header("2 · Route × lead-time heatmap")
if heat.empty:
    st.info("No lead-time buckets are available for this dataset.")
else:
    pivot = heat.pivot(index="route", columns="lead_bucket", values="total_fare")
    st.plotly_chart(px.imshow(pivot, labels={"x":"Lead-time bucket", "y":"Route", "color":"Mean fare (INR)"}, aspect="auto", color_continuous_scale="YlOrRd"), use_container_width=True)
    st.download_button("Download heatmap data CSV", heat.to_csv(index=False), "apix_heatmap.csv", "text/csv")

st.header("3 · Lead-time elasticity")
if curve.empty:
    st.info("This dataset has no booking lead-time field.")
else:
    st.plotly_chart(px.line(curve, x="lead_bucket", y="mean_fare", color="route", markers=True, labels={"mean_fare":"Mean fare (INR)","lead_bucket":"Booking lead time"}), use_container_width=True)
    st.dataframe(curve, use_container_width=True)
    st.download_button("Download lead-time curve CSV", curve.to_csv(index=False), "apix_lead_time.csv", "text/csv")

st.header("4 · Carrier comparison")
if carrier.empty:
    st.info("No carrier rows available.")
else:
    st.plotly_chart(px.bar(carrier.sort_values("mean_fare"), x="carrier", y="mean_fare", hover_data=["median_fare", "quotes"], labels={"mean_fare":"Mean fare (INR)", "carrier":"Carrier"}), use_container_width=True)
    st.download_button("Download carrier table CSV", carrier.to_csv(index=False), "apix_carriers.csv", "text/csv")

st.header("5 · Data quality")
st.json(quality_report(dataset))

st.header("6 · Backtest vs DGCA")
dgca = load_dgca()
if dgca.empty:
    st.info("DGCA reference data not loaded yet. Fill data/external/dgca_monthly.csv with sourced monthly reference fares and rebuild or refresh the app.")
else:
    st.info("A meaningful backtest needs a dated APIx series; this dataset currently has no confirmed quote-observation date. Any comparison will be short and exploratory.")

st.header("7 · Methodology and limitations")
st.markdown("""
- The headline methodology is a Jevons geometric mean of fare relatives within route × carrier × cabin × lead-time cells, then route-weighted.
- The EaseMyTrip lead-time source has no calendar date, so it cannot support a time-series inflation index. The Goibibo date field is not confirmed as a quote-observation date and has no booking lead-time field.
- Route weights are marked placeholders. Total prices have no base/tax split; those schema fields remain null.
- These historical snapshots are from 2022 and 2023, not current fares. Airline/carrier and route composition can change.
- This prototype reads only committed files under `data/processed/` and makes no network calls.
""")


