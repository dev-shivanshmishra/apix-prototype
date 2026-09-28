import pandas as pd

from apix.loaders import load_easemytrip


def test_loader_schema_and_city_mapping():
    result = load_easemytrip("tests/fixtures/easemytrip_small.csv")
    assert list(result.columns) == ["obs_date", "origin", "destination", "route", "carrier", "flight_no", "cabin_class", "lead_time_days", "stops", "duration_hours", "base_fare", "taxes", "total_fare", "source_dataset"]
    assert result.iloc[0].route == "BLR-DEL"
    assert pd.isna(result.iloc[0].obs_date)
    assert pd.isna(result.iloc[0].base_fare)
