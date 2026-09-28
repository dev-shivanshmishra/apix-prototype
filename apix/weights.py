"""Route weight loading and normalisation."""
from pathlib import Path

import pandas as pd

from apix.config import EXTERNAL_DIR


def load_route_weights(path: str | Path | None = None) -> pd.DataFrame:
    """Load route passenger weights, normalising placeholder or observed counts to one."""
    path = Path(path) if path else EXTERNAL_DIR / "route_weights.csv"
    df = pd.read_csv(path)
    if not {"route", "passengers", "weight"}.issubset(df.columns):
        raise ValueError("route_weights.csv needs route,passengers,weight columns")
    df["weight"] = pd.to_numeric(df["passengers"], errors="coerce").fillna(0).clip(lower=0)
    total = df["weight"].sum()
    df["weight"] = df["weight"] / total if total else 1 / max(len(df), 1)
    if "is_placeholder" not in df:
        df["is_placeholder"] = False
    return df


def renormalize_weights(weights: pd.DataFrame, routes: set[str]) -> pd.DataFrame:
    """Keep available routes and renormalise their weights to sum to one."""
    out = weights[weights.route.isin(routes)].copy()
    total = out.weight.sum()
    if total > 0:
        out["weight"] /= total
    return out
