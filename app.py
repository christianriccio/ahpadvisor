import json
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd
import os
import streamlit as st

from src.ahp import (
    SAATY_SCALE,
    aggregate_pairwise_matrices,
    build_pairwise_matrix,
    consistency_ratio,
    matrix_to_json,
    weights_geometric_mean,
)
from src.data import (
    REQUIRED_COLUMNS,
    coerce_numeric,
    dataset_hash,
    demo_dataset,
    load_dataframe,
    validate_ranges,
    validate_schema,
)
from src.db import fetch_votes, init_db, parse_vote_matrices, save_vote
from src.scoring import MACRO_CRITERIA, compute_macro_scores, normalize_min_max, rank_alternatives

import plotly.graph_objects as go

try:
    from streamlit import st_autorefresh
except Exception:
    st_autorefresh = None


DB_PATH = os.getenv("AHP_DB_PATH", "data/ahp.db")


def init_state():
    if "dataset" not in st.session_state:
        st.session_state.dataset = None
    if "dataset_hash" not in st.session_state:
        st.session_state.dataset_hash = None


def load_demo():
    df = demo_dataset()
    st.session_state.dataset = df
    st.session_state.dataset_hash = dataset_hash(df)


def load_upload(file):
    df = load_dataframe(file)
    df = coerce_numeric(df)
    st.session_state.dataset = df
    st.session_state.dataset_hash = dataset_hash(df)


def data_setup_section():
    st.header("Setup dati")

    upload = st.file_uploader("Carica Excel o CSV", type=["xlsx", "csv"])
    if upload is not None:
        load_upload(upload)

    if st.button("Usa dataset demo"):
        load_demo()

    if st.session_state.dataset is None:
        st.info("Carica un file oppure usa il dataset demo.")
        return

    df = st.session_state.dataset
    st.subheader("Anteprima")
    st.dataframe(df.head(10))

    ok, missing = validate_schema(df)
    if not ok:
        st.error(f"Colonne mancanti: {', '.join(missing)}")
        return

    range_issues = validate_ranges(df)
    if range_issues:
        st.warning(f"Valori fuori range 1-5 nelle colonne: {', '.join(range_issues)}")

    st.success("Schema valido.")


def vote_section():
    st.header("Vota")

    if st.session_state.dataset is None:
        st.info("Carica prima un dataset nella pagina Setup dati.")
        return
    ok, missing = validate_schema(st.session_state.dataset)
    if not ok:
        st.error(f"Dataset non valido. Colonne mancanti: {', '.join(missing)}")
        return

    user_name = st.text_input("Nome o nickname", max_chars=50)
    if not user_name:
        st.warning("Il nome è obbligatorio.")
        return

    criteria = MACRO_CRITERIA
    pairs = [
        (criteria[0], criteria[1]),
        (criteria[0], criteria[2]),
        (criteria[1], criteria[2]),
    ]

    scale_values = {0: 1, 1: 3, 2: 5, 3: 7, 4: 9}
    scale_labels = {
        -4: "Estremamente più importante (B)",
        -3: "Molto fortemente più importante (B)",
        -2: "Fortemente più importante (B)",
        -1: "Moderatamente più importante (B)",
        0: "Uguale",
        1: "Moderatamente più importante (A)",
        2: "Fortemente più importante (A)",
        3: "Molto fortemente più importante (A)",
        4: "Estremamente più importante (A)",
    }

    comparisons: Dict[tuple, float] = {}
    for a, b in pairs:
        st.subheader(f"Confronto: {a} vs {b}")
        slider_val = st.slider(
            f"{a} rispetto a {b}",
            min_value=-4,
            max_value=4,
            value=0,
            step=1,
            format="",
            key=f"slider_{a}_{b}",
        )
        st.caption(scale_labels[slider_val])
        if slider_val == 0:
            value = 1.0
        elif slider_val > 0:
            value = float(scale_values[slider_val])
        else:
            value = 1.0 / float(scale_values[abs(slider_val)])
        comparisons[(a, b)] = value

    matrix = build_pairwise_matrix(criteria, comparisons)
    weights = weights_geometric_mean(matrix)
    cr = consistency_ratio(matrix, weights)

    st.subheader("Pesi utente")
    st.write({criteria[i]: round(float(weights[i]), 4) for i in range(len(criteria))})
    st.write(f"Consistency Ratio (CR): {cr:.4f}")

    if cr >= 0.10:
        st.warning("CR >= 0.10. Rivedi i confronti per maggiore coerenza.")

    if st.button("Invia voto"):
        try:
            init_db()
        except Exception as exc:
            st.error(f"DB non raggiungibile: {exc}")
            return
        weights_json = json.dumps({criteria[i]: float(weights[i]) for i in range(len(criteria))})
        save_vote(
            user_name=user_name,
            dataset_hash=st.session_state.dataset_hash,
            pairwise_matrix_json=matrix_to_json(matrix),
            weights_json=weights_json,
            cr=float(cr),
            created_at=datetime.utcnow().isoformat(),
        )
        st.success("Voto salvato.")


def results_section():
    st.header("Risultati")

    if st.session_state.dataset is None:
        st.info("Carica prima un dataset nella pagina Setup dati.")
        return
    ok, missing = validate_schema(st.session_state.dataset)
    if not ok:
        st.error(f"Dataset non valido. Colonne mancanti: {', '.join(missing)}")
        return

    try:
        init_db()
        rows = fetch_votes(st.session_state.dataset_hash)
    except Exception as exc:
        st.error(f"DB non raggiungibile: {exc}")
        return
    st.write(f"Numero voti: {len(rows)}")

    if st_autorefresh is not None:
        auto = st.checkbox("Auto-refresh (10s)")
        if auto:
            st_autorefresh(interval=10000, key="auto_refresh")

    if st.button("Aggiorna"):
        st.experimental_rerun()

    if rows:
        matrices = parse_vote_matrices(rows)
        group_matrix = aggregate_pairwise_matrices(matrices)
        group_weights = weights_geometric_mean(group_matrix)
        group_cr = consistency_ratio(group_matrix, group_weights)
    else:
        group_weights = np.array([1 / 3, 1 / 3, 1 / 3])
        group_cr = 0.0

    st.subheader("Pesi di gruppo")
    st.write({MACRO_CRITERIA[i]: round(float(group_weights[i]), 4) for i in range(3)})
    st.write(f"CR gruppo: {group_cr:.4f}")

    weights_dict = {MACRO_CRITERIA[i]: float(group_weights[i]) for i in range(3)}
    ranking = rank_alternatives(st.session_state.dataset, weights_dict)

    if ranking.empty:
        st.warning("Nessun locale con dati completi per il ranking.")
        return

    st.subheader("Ranking locali")
    st.dataframe(ranking)
    st.success(f"Raccomandato: {ranking.iloc[0]['LOCALI']}")

    top = ranking.head(5).copy()
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=top["LOCALI"], y=top["score"], marker_color="#1f77b4"))
    fig_bar.update_layout(title="Top 5 - Punteggio", xaxis_title="Locale", yaxis_title="Score")
    st.plotly_chart(fig_bar, use_container_width=True)

    macro_scores = compute_macro_scores(st.session_state.dataset)
    macro_norm = normalize_min_max(macro_scores)
    radar = go.Figure()
    for locale in top["LOCALI"]:
        if locale not in macro_norm.index:
            continue
        radar.add_trace(
            go.Scatterpolar(
                r=[macro_norm.loc[locale, c] for c in MACRO_CRITERIA],
                theta=MACRO_CRITERIA,
                fill="toself",
                name=str(locale),
            )
        )
    radar.update_layout(title="Radar - Macro-criteri (Top 5)", polar=dict(radialaxis=dict(visible=True)))
    st.plotly_chart(radar, use_container_width=True)

    st.subheader("Dettaglio macro e sotto-criteri (Top 5)")
    detail = st.session_state.dataset.copy()
    detail = detail[detail["LOCALI"].isin(top["LOCALI"])]
    detail = detail.groupby("LOCALI", dropna=False).mean(numeric_only=True)
    st.dataframe(detail.loc[top["LOCALI"]])


def main():
    st.set_page_config(page_title="AHPadvisor", layout="wide")
    st.title("AHPadvisor")

    init_state()
    data_setup_section()
    st.divider()
    vote_section()
    st.divider()
    results_section()


if __name__ == "__main__":
    main()
