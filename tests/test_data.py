import pandas as pd

from src.data import REQUIRED_COLUMNS, coerce_numeric, dataset_hash, demo_dataset, load_dataframe, validate_ranges, validate_schema


def test_demo_dataset_schema():
    df = demo_dataset()
    ok, missing = validate_schema(df)
    assert ok
    assert missing == []


def test_coerce_and_ranges():
    df = demo_dataset()
    df = coerce_numeric(df)
    issues = validate_ranges(df)
    assert issues == []


def test_dataset_hash_stable():
    df = demo_dataset()
    h1 = dataset_hash(df)
    h2 = dataset_hash(df)
    assert h1 == h2


def test_load_excel(tmp_path):
    df = demo_dataset()
    path = tmp_path / "data.xlsx"
    df.to_excel(path, index=False)
    with open(path, "rb") as f:
        loaded = load_dataframe(f)
    ok, _ = validate_schema(loaded)
    assert ok
