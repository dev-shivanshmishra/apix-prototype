"""Build compact processed parquet files from user-provided raw CSVs."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd

from apix.cleaning import clean_fares
from apix.config import EXTERNAL_DIR, PROCESSED_DIR, RAW_DIR
from apix.loaders import load_easemytrip, load_goibibo


def save(name: str, frame: pd.DataFrame) -> None:
    clean, report = clean_fares(frame)
    clean.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False, compression="zstd")
    (PROCESSED_DIR / f"{name}_quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{name}: {report['rows_in']:,} input -> {len(clean):,} clean; {(PROCESSED_DIR / f'{name}.parquet').stat().st_size / 1_000_000:.2f} MB; {report}")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    routes = set()
    clean_path = RAW_DIR / "Clean_Dataset.csv"
    if clean_path.exists():
        fares = load_easemytrip(clean_path)
        routes.update(fares.route.dropna().unique())
        save("easemytrip", fares)
    goibibo_path = RAW_DIR / "goibibo_flights_data.csv"
    if goibibo_path.exists():
        fares = load_goibibo(goibibo_path)
        source_dates = pd.read_csv(goibibo_path, usecols=["flight date"])["flight date"]
        fares["_source_date_key"] = source_dates.astype("string").fillna("").values
        routes.update(fares.route.dropna().unique())
        save("goibibo", fares)
    weight_path = EXTERNAL_DIR / "route_weights.csv"
    if not weight_path.exists():
        pd.DataFrame([{"route": route, "passengers": 1, "weight": "PLACEHOLDER", "is_placeholder": True} for route in sorted(routes)]).to_csv(weight_path, index=False)
    dgca_path = EXTERNAL_DIR / "dgca_monthly.csv"
    if not dgca_path.exists():
        pd.DataFrame(columns=["month", "avg_domestic_fare_inr", "source_url", "notes"]).to_csv(dgca_path, index=False)
    print("Build complete. Placeholder route weights and empty DGCA template are at data/external/.")


if __name__ == "__main__":
    main()


