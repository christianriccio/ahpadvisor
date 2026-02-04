# AHPadvisor

Web app Streamlit per decisione di gruppo con AHP-Express sui macro-criteri.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app.py
```

## Deploy / Online
- Usa `AHP_DB_PATH` per puntare a un file SQLite persistente (es. volume o path su server).
- Streamlit Community Cloud: ideale per demo rapide, ma il filesystem può essere effimero. Per votazioni reali multi-utente usa un DB esterno.
- Consigliato: Postgres (es. Supabase). Imposta `DATABASE_URL` nei secrets di Streamlit.
- Alternativa: VPS/VM (Docker o `systemd`) con storage persistente e porta esposta.

### Streamlit Community Cloud + Supabase (sintesi)
1. Crea progetto Supabase e prendi la connection string Postgres.
2. Metti `DATABASE_URL` nei Secrets di Streamlit Cloud.
3. Pubblica la repo su GitHub e crea app su Streamlit Cloud.

## Dati attesi
Colonna obbligatoria: `LOCALI`.

Macro-criteri (Liv1):
- `Comodità`
- `Cibo e bevande`
- `Rapporto qualità/prezzo`

Sotto-criteri (Liv2) usati per lo scoring:
- `Location`, `Parcheggio`, `Qualità/Prezzo`, `Pubblic Relation`, `Primi`, `Carne`, `Pesce`, `Panini`, `Pizza`, `Birra`, `Vino`, `Veg`

## Regole metodologiche
- AHP-Express applicato ai soli macro-criteri (3x3).
- Aggregazione di gruppo: media geometrica elemento-per-elemento delle matrici.
- Scoring macro per locale: media dei sotto-criteri disponibili (NaN ignorati). Se tutti NaN, macro score = NaN e la riga viene esclusa dal ranking.
- Normalizzazione macro-score: min-max per criterio (0-1). Se criterio costante, valore normalizzato = 0.5.
- Policy duplicati voti: un nuovo voto dello stesso `user_name` sovrascrive quello precedente per lo stesso dataset.

## Struttura
- `app.py`: UI Streamlit (Setup dati, Vota, Risultati)
- `src/data.py`: load/validate/normalize
- `src/ahp.py`: AHP utilities, CR, aggregazione
- `src/scoring.py`: Liv2→macro + ranking
- `src/db.py`: SQLite votes
- `tests/`: pytest
