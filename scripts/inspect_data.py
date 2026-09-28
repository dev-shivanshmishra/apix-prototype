from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
KEY_CATEGORICALS = ["airline", "carrier", "source_city", "destination_city", "from", "to", "class", "stops"]
DATE_COLUMNS = ["obs_date", "flight_date", "flight date", "date", "departure_date", "travel_date"]


def main() -> None:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {RAW_DIR}")
        return
    for path in files:
        print(f"\n=== {path.name} ===")
        try:
            df = pd.read_csv(path, low_memory=False)
        except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            print(f"Could not read CSV: {exc}")
            continue
        print(f"Rows: {len(df):,}; columns: {len(df.columns)}")
        print("Columns:", list(df.columns))
        print("Dtypes:\n", df.dtypes.to_string())
        for column in DATE_COLUMNS:
            if column in df:
                dates = pd.to_datetime(df[column], errors="coerce", dayfirst=True)
                print(f"Date range ({column}): {dates.min()} .. {dates.max()} ({dates.notna().sum():,} parseable)")
        for column in KEY_CATEGORICALS:
            if column in df:
                values = df[column].dropna().astype(str).unique()
                print(f"Unique {column} ({len(values):,}): {list(values[:40])}")


if __name__ == "__main__":
    main()



