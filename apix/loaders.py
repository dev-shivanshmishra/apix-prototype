"""Load historical source CSVs into the stable APIx fare schema."""
import re
from pathlib import Path

import pandas as pd

from apix.config import CANONICAL_COLUMNS, CITY_TO_IATA, RAW_DIR


def _city(value: object) -> str | None:
    if pd.isna(value):
        return None
    key = re.sub(r"[^a-z]", "", str(value).lower())
    return CITY_TO_IATA.get(key)


def _duration(value: object) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", str(value).lower())
        if not match or not any(match.groups()):
            return None
        return int(match.group(1) or 0) + int(match.group(2) or 0) / 60


def _canonical(df: pd.DataFrame, source: str, *, origin: str, destination: str, carrier: str, flight: str | None, cabin: str, lead: str | None, stops: str, duration: str, price: str, obs_date: str | None = None) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["obs_date"] = pd.to_datetime(df[obs_date], errors="coerce") if obs_date and obs_date in df else pd.NaT
    out["origin"] = df[origin].map(_city)
    out["destination"] = df[destination].map(_city)
    out["route"] = out["origin"].fillna("") + "-" + out["destination"].fillna("")
    out.loc[out["origin"].isna() | out["destination"].isna(), "route"] = None
    out["carrier"] = df[carrier].astype("string").str.strip()
    out["flight_no"] = df[flight].astype("string").str.strip() if flight and flight in df else pd.NA
    out["cabin_class"] = df[cabin].astype("string").str.strip().str.title() if cabin in df else "Unknown"
    out["lead_time_days"] = pd.to_numeric(df[lead], errors="coerce") if lead and lead in df else pd.NA
    out["stops"] = df[stops].astype("string").str.strip() if stops in df else pd.NA
    out["duration_hours"] = df[duration].map(_duration) if duration in df else pd.NA
    out["base_fare"] = pd.NA
    out["taxes"] = pd.NA
    out["total_fare"] = pd.to_numeric(df[price].astype("string").str.replace(r"[^0-9.]", "", regex=True), errors="coerce")
    out["source_dataset"] = source
    return out[CANONICAL_COLUMNS]


def load_easemytrip(path: str | Path | None = None) -> pd.DataFrame:
    """Load EaseMyTrip Clean_Dataset.csv; its `days_left` is lead time, not a date."""
    path = Path(path) if path else RAW_DIR / "Clean_Dataset.csv"
    raw = pd.read_csv(path, low_memory=False)
    return _canonical(raw, "easemytrip", origin="source_city", destination="destination_city", carrier="airline", flight="flight", cabin="class", lead="days_left", stops="stops", duration="duration", price="price")


def load_goibibo(path: str | Path | None = None) -> pd.DataFrame:
    """Load Goibibo data. `flight date` is retained as its source date field; semantics need confirmation."""
    path = Path(path) if path else RAW_DIR / "goibibo_flights_data.csv"
    raw = pd.read_csv(path, low_memory=False)
    return _canonical(raw, "goibibo", origin="from", destination="to", carrier="airline", flight="flight_num", cabin="class", lead=None, stops="stops", duration="duration", price="price", obs_date=None)

