import hashlib
from typing import List, Tuple

import os
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "LOCALI",
    "Location",
    "Parcheggio",
    "Qualità/Prezzo",
    "Pubblic Relation",
    "Primi",
    "Carne",
    "Pesce",
    "Panini",
    "Pizza",
    "Birra",
    "Vino",
    "Veg",
]


def _fill_missing_ratings(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    df = df.copy()
    rng = np.random.default_rng(seed)
    for col in df.columns:
        if col in ["LOCALI", "TIPOLOGIA", "Indirizzo"]:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            mask = df[col].isna()
            if mask.any():
                df.loc[mask, col] = rng.integers(1, 6, size=mask.sum())
    return df


def demo_dataset() -> pd.DataFrame:
    demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "demo_locali.xlsx")
    if os.path.exists(demo_path):
        df = pd.read_excel(demo_path)
        df = coerce_numeric(df)
        df = _fill_missing_ratings(df)
        return df

    data = {
        "LOCALI": ["Osteria Alba", "Pub 9", "Enoteca Centro", "Trattoria Luna"],
        "Location": [4, 3, 5, 4],
        "Parcheggio": [3, 2, 4, 3],
        "Qualità/Prezzo": [4, 3, 5, 4],
        "Pubblic Relation": [4, 3, 4, 5],
        "Primi": [5, 3, 4, 5],
        "Carne": [4, 4, 3, 5],
        "Pesce": [3, 2, 5, 3],
        "Panini": [3, 5, 2, 3],
        "Pizza": [4, 4, 3, 4],
        "Birra": [3, 5, 2, 3],
        "Vino": [4, 3, 5, 4],
        "Veg": [3, 2, 4, 3],
    }
    return pd.DataFrame(data)


def load_dataframe(file) -> pd.DataFrame:
    name = getattr(file, "name", "")
    if name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return df


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, missing
    return True, []


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col == "LOCALI":
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def validate_ranges(df: pd.DataFrame, min_val: float = 1.0, max_val: float = 5.0) -> List[str]:
    issues = []
    for col in REQUIRED_COLUMNS:
        if col == "LOCALI":
            continue
        series = df[col].dropna()
        if not series.empty:
            if (series < min_val).any() or (series > max_val).any():
                issues.append(col)
    return issues


def dataset_hash(df: pd.DataFrame) -> str:
    cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    stable = df[cols].copy()
    stable = stable.sort_values("LOCALI").reset_index(drop=True)
    payload = stable.to_csv(index=False)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()
