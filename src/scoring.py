from typing import Dict

import numpy as np
import pandas as pd

MACRO_CRITERIA = ["Comodità", "Cibo e bevande", "Rapporto qualità/prezzo"]

MACRO_MAP = {
    "Comodità": ["Location", "Parcheggio", "Pubblic Relation"],
    "Cibo e bevande": ["Primi", "Carne", "Pesce", "Panini", "Pizza", "Birra", "Vino", "Veg"],
    "Rapporto qualità/prezzo": ["Qualità/Prezzo"],
}


def _mean_ignore_nan(values: pd.Series) -> float:
    if values.dropna().empty:
        return np.nan
    return float(values.mean(skipna=True))


def compute_macro_scores(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("LOCALI", dropna=False).mean(numeric_only=True)
    macro_scores = pd.DataFrame(index=grouped.index)
    for macro, cols in MACRO_MAP.items():
        available = [c for c in cols if c in grouped.columns]
        macro_scores[macro] = grouped[available].apply(_mean_ignore_nan, axis=1)
    return macro_scores


def normalize_min_max(df: pd.DataFrame) -> pd.DataFrame:
    normed = df.copy()
    for col in normed.columns:
        series = normed[col]
        if series.dropna().empty:
            continue
        min_v = series.min(skipna=True)
        max_v = series.max(skipna=True)
        if min_v == max_v:
            normed[col] = 0.5
        else:
            normed[col] = (series - min_v) / (max_v - min_v)
    return normed


def rank_alternatives(df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    macro_scores = compute_macro_scores(df)
    macro_scores = macro_scores[MACRO_CRITERIA]
    normed = normalize_min_max(macro_scores)

    # Exclude rows with any NaN macro score
    valid = normed.dropna(axis=0, how="any")
    if valid.empty:
        return pd.DataFrame(columns=["LOCALI", "score"])

    weight_series = pd.Series(weights)
    weight_series = weight_series.reindex(MACRO_CRITERIA).fillna(0)
    scores = valid.mul(weight_series, axis=1).sum(axis=1)

    result = scores.sort_values(ascending=False).reset_index()
    result.columns = ["LOCALI", "score"]
    return result
