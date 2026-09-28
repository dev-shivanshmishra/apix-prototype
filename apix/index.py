"""Jevons elementary aggregates and fixed-base/chain-linked indices."""
import numpy as np
import pandas as pd

from apix.cleaning import assign_lead_bucket
from apix.weights import renormalize_weights

CELL = ["route", "carrier", "cabin_class", "lead_bucket"]


def lead_time_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return route-level bucket curves, route/bucket heatmap values and carriers."""
    data = df.copy()
    data["lead_bucket"] = data.lead_time_days.map(assign_lead_bucket)
    data = data[data.lead_bucket.notna()]
    curve = data.groupby(["route", "lead_bucket"], as_index=False).agg(mean_fare=("total_fare", "mean"), median_fare=("total_fare", "median"))
    base = curve[curve.lead_bucket.eq("T+45")].set_index("route").mean_fare
    curve["normalised_mean"] = curve.apply(lambda row: row.mean_fare / base.get(row.route, np.nan) * 100, axis=1)
    heat = data.groupby(["route", "lead_bucket"], as_index=False).total_fare.mean()
    carrier = data.groupby("carrier", as_index=False).agg(mean_fare=("total_fare", "mean"), median_fare=("total_fare", "median"), quotes=("total_fare", "size"))
    return curve, heat, carrier


def compute_index(df: pd.DataFrame, weights: pd.DataFrame, *, chain_link: bool = False) -> pd.DataFrame:
    """Compute daily route-weighted Jevons index for dated fare observations.

    Cells are route x carrier x cabin class x lead bucket. The base is the
    first complete Monday-Sunday week represented by all seven dates.
    """
    data = df[df.obs_date.notna() & df.total_fare.gt(0)].copy()
    if data.empty:
        return pd.DataFrame(columns=["obs_date", "index"])
    data["obs_date"] = pd.to_datetime(data.obs_date).dt.normalize()
    data["lead_bucket"] = data.lead_time_days.map(assign_lead_bucket)
    data = data[data.lead_bucket.notna()]
    if data.empty:
        return pd.DataFrame(columns=["obs_date", "index"])
    data["cell"] = data[CELL].astype(str).agg("|".join, axis=1)
    daily = data.groupby(["obs_date", "route", "cell"], as_index=False).total_fare.agg(lambda x: float(np.exp(np.log(x).mean())))
    dates = sorted(daily.obs_date.unique())
    full_week = None
    for start in dates:
        week = pd.date_range(start, periods=7, freq="D")
        if start.weekday() == 0 and set(week).issubset(set(dates)):
            full_week = week
            break
    if full_week is None:
        return pd.DataFrame(columns=["obs_date", "index"])
    base = daily[daily.obs_date.isin(full_week)].groupby(["route", "cell"]).total_fare.apply(lambda x: float(np.exp(np.log(x).mean()))).rename("base")
    joined = daily.join(base, on=["route", "cell"])
    joined["relative"] = joined.total_fare / joined.base
    route_rel = joined.groupby(["obs_date", "route"]).relative.apply(lambda x: float(np.exp(np.log(x).mean()))).rename("relative").reset_index()
    output = []
    previous = None
    for date, group in route_rel.groupby("obs_date"):
        active = renormalize_weights(weights, set(group.route))
        merged = group.merge(active[["route", "weight"]], on="route")
        if merged.empty:
            continue
        relative = float(np.exp((np.log(merged.relative) * merged.weight).sum()))
        if chain_link:
            if previous is None:
                value = 100.0
            else:
                prior_group = route_rel[route_rel.obs_date.eq(previous)]
                shared = set(group.route) & set(prior_group.route)
                if shared:
                    prior = prior_group[prior_group.route.isin(shared)].set_index("route").relative
                    current = group[group.route.isin(shared)].set_index("route").relative
                    route_weights = renormalize_weights(weights, shared).set_index("route").weight
                    link = float(np.exp((np.log(current / prior) * route_weights).sum()))
                    value = output[-1]["index"] * link
                else:
                    value = relative * 100
        else:
            value = relative * 100
        output.append({"obs_date": pd.Timestamp(date), "index": value})
        previous = date
    return pd.DataFrame(output)


def aggregate_index(daily: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """Aggregate daily index by calendar week (`W`) or month (`MS`) using mean."""
    if daily.empty:
        return pd.DataFrame(columns=["period", "index"])
    period = "W" if freq == "W" else "M"
    return daily.assign(period=pd.to_datetime(daily.obs_date).dt.to_period(period).astype(str)).groupby("period", as_index=False)["index"].mean()
