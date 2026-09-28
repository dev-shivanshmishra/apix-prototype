"""Fare validation and robust within-cell outlier filtering."""
import pandas as pd

from apix.config import LEAD_BUCKETS


def assign_lead_bucket(days: object, tolerance: int = 2) -> str | None:
    """Assign days to the nearest configured lead bucket, or None beyond tolerance."""
    try:
        value = float(days)
    except (TypeError, ValueError):
        return None
    nearest = min(LEAD_BUCKETS, key=lambda target: abs(value - target))
    return LEAD_BUCKETS[nearest] if abs(value - nearest) <= tolerance else None


def clean_fares(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Drop invalid/duplicate quotes and fare outliers within route/class/lead cells."""
    report = {"rows_in": len(df), "exact_duplicates": 0, "invalid_fare": 0, "unparseable_route": 0, "outliers": 0, "rows_out": 0}
    out = df.copy()
    duplicated = out.duplicated()
    report["exact_duplicates"] = int(duplicated.sum())
    out = out.loc[~duplicated].copy()
    fare = pd.to_numeric(out["total_fare"], errors="coerce")
    bad_fare = fare.isna() | (fare <= 0)
    report["invalid_fare"] = int(bad_fare.sum())
    out = out.loc[~bad_fare].copy()
    bad_route = out["route"].isna() | ~out["route"].astype(str).str.fullmatch(r"[A-Z]{3}-[A-Z]{3}")
    report["unparseable_route"] = int(bad_route.sum())
    out = out.loc[~bad_route].copy()
    out["total_fare"] = pd.to_numeric(out["total_fare"])
    out["lead_bucket"] = out.get("lead_time_days", pd.Series(index=out.index, dtype=float)).map(assign_lead_bucket)
    keys = ["route", "cabin_class", "lead_bucket"]
    keep = pd.Series(True, index=out.index)
    for _, group in out.groupby(keys, dropna=False):
        values = group["total_fare"]
        if len(group) >= 20:
            q1, q3 = values.quantile([0.25, 0.75])
            low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        else:
            median = values.median()
            mad = (values - median).abs().median()
            spread = 3 * 1.4826 * mad if mad else 0
            low, high = max(0, median - spread), median + spread
        keep.loc[group.index] = values.between(low, high, inclusive="both")
    report["outliers"] = int((~keep).sum())
    out = out.loc[keep].copy()
    report["rows_out"] = len(out)
    return out.reset_index(drop=True), report
