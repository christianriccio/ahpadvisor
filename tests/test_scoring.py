from src.data import demo_dataset
from src.scoring import compute_macro_scores, rank_alternatives


def test_compute_macro_scores():
    df = demo_dataset()
    macro = compute_macro_scores(df)
    assert not macro.empty
    assert set(macro.columns) == {"Comodità", "Cibo e bevande", "Rapporto qualità/prezzo"}


def test_rank_alternatives():
    df = demo_dataset()
    weights = {"Comodità": 1 / 3, "Cibo e bevande": 1 / 3, "Rapporto qualità/prezzo": 1 / 3}
    ranking = rank_alternatives(df, weights)
    assert not ranking.empty
    assert list(ranking.columns) == ["LOCALI", "score"]
    assert ranking.iloc[0]["score"] >= ranking.iloc[-1]["score"]
