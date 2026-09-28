"""Compare monthly APIx movement with a user-supplied DGCA reference series."""
from pathlib import Path

import pandas as pd

from apix.config import EXTERNAL_DIR


def load_dgca(path: str | Path | None = None) -> pd.DataFrame:
    """Read the DGCA template, returning an empty frame when it is unfilled."""
    path = Path(path) if path else EXTERNAL_DIR / "dgca_monthly.csv"
    df = pd.read_csv(path)
    if "month" not in df or "avg_domestic_fare_inr" not in df:
        return pd.DataFrame(columns=["month", "avg_domestic_fare_inr"])
    df["avg_domestic_fare_inr"] = pd.to_numeric(df["avg_domestic_fare_inr"], errors="coerce")
    return df.dropna(subset=["month", "avg_domestic_fare_inr"])


def compare_monthly(apix_monthly: pd.DataFrame, dgca: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    """Compare MoM percent changes and return agreement, Pearson r and MAE."""
    a = apix_monthly.copy()
    a["month"] = pd.PeriodIndex(a["period"], freq="M").astype(str)
    a["apix_change_pct"] = pd.to_numeric(a["index"]).pct_change() * 100
    d = dgca.copy()
    d["month"] = pd.PeriodIndex(d["month"], freq="M").astype(str)
    d["dgca_change_pct"] = pd.to_numeric(d["avg_domestic_fare_inr"]).pct_change() * 100
    joined = a.merge(d[["month", "dgca_change_pct"]], on="month").dropna(subset=["apix_change_pct", "dgca_change_pct"])
    stats: dict[str, float | int | None] = {"points": len(joined), "direction_agreement_pct": None, "pearson_r": None, "mae": None}
    if len(joined):
        stats["direction_agreement_pct"] = float((joined.apix_change_pct.gt(0) == joined.dgca_change_pct.gt(0)).mean() * 100)
    if len(joined) >= 3:
        stats["pearson_r"] = float(joined.apix_change_pct.corr(joined.dgca_change_pct))
        stats["mae"] = float((joined.apix_change_pct - joined.dgca_change_pct).abs().mean())
    return joined, stats
