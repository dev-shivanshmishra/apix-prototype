from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
EXTERNAL_DIR = ROOT / "data" / "external"
CITY_TO_IATA = {"delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR", "bengaluru": "BLR", "kolkata": "CCU", "hyderabad": "HYD", "chennai": "MAA"}
LEAD_BUCKETS = {1: "T+1", 7: "T+7", 15: "T+15", 30: "T+30", 45: "T+45"}
LEAD_TOLERANCE_DAYS = 2
CANONICAL_COLUMNS = ["obs_date", "origin", "destination", "route", "carrier", "flight_no", "cabin_class", "lead_time_days", "stops", "duration_hours", "base_fare", "taxes", "total_fare", "source_dataset"]
