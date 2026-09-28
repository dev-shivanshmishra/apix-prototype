import numpy as np
import pandas as pd

from apix.cleaning import assign_lead_bucket, clean_fares
from apix.index import compute_index
from apix.weights import load_route_weights


def test_lead_bucket_edges():
    assert assign_lead_bucket(1) == "T+1"
    assert assign_lead_bucket(3) == "T+1"
    assert assign_lead_bucket(4) is None
    assert assign_lead_bucket(47) == "T+45"


def test_cleaning_duplicates_invalid_and_outlier():
    rows = [{"route":"DEL-BOM", "cabin_class":"Economy", "lead_time_days":1, "total_fare":100.0 + i} for i in range(20)]
    rows += [{"route":"DEL-BOM", "cabin_class":"Economy", "lead_time_days":1, "total_fare":10000.0}, {"route":"DEL-BOM", "cabin_class":"Economy", "lead_time_days":1, "total_fare":-2}, rows[0].copy(), {"route":"?", "cabin_class":"Economy", "lead_time_days":1, "total_fare":200}]
    clean, report = clean_fares(pd.DataFrame(rows))
    assert report["exact_duplicates"] == 1
    assert report["invalid_fare"] == 1
    assert report["unparseable_route"] == 1
    assert report["outliers"] == 1
    assert len(clean) == 20


def test_index_base_and_weighted_geometric_mean():
    dates = pd.date_range("2024-01-01", periods=9)
    frame = []
    for day in dates:
        for route, base, mult in [("DEL-BOM",100,1), ("BOM-DEL",200,2 if day >= dates[7] else 1)]:
            frame.append({"obs_date":day,"route":route,"carrier":"X","cabin_class":"Economy","lead_time_days":1,"total_fare":base*mult})
    weights = pd.DataFrame({"route":["DEL-BOM","BOM-DEL"],"weight":[.75,.25]})
    result = compute_index(pd.DataFrame(frame), weights)
    assert np.isclose(result.iloc[0]["index"], 100)
    assert np.isclose(result.iloc[-1]["index"], 100 * (2 ** .25))


def test_weight_normalisation_and_missing_route_renormalisation(tmp_path):
    path = tmp_path / "weights.csv"
    pd.DataFrame({"route":["DEL-BOM","BOM-DEL"],"passengers":[3,1],"weight":[.2,.8],"is_placeholder":[True,True]}).to_csv(path,index=False)
    weights = load_route_weights(path)
    assert np.isclose(weights.weight.sum(), 1)
    from apix.weights import renormalize_weights
    subset = renormalize_weights(weights,{"DEL-BOM"})
    assert len(subset) == 1 and subset.iloc[0].weight == 1




