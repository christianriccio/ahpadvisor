import json
import os
import socket
import sqlite3
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from typing import List, Tuple

from .ahp import matrix_from_json

try:
    import psycopg
except Exception:
    psycopg = None

try:
    import psycopg2
except Exception:
    psycopg2 = None


def _get_backend():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return "postgres", _normalize_db_url(db_url)
    return "sqlite", os.getenv("AHP_DB_PATH", "data/ahp.db")


def _normalize_db_url(db_url: str) -> str:
    parsed = urlparse(db_url)
    if parsed.scheme not in ("postgres", "postgresql"):
        return db_url

    qs = parse_qs(parsed.query)
    if "sslmode" not in qs and parsed.hostname:
        if parsed.hostname.endswith("supabase.co") or parsed.hostname.endswith("neon.tech"):
            qs["sslmode"] = ["require"]

    if "hostaddr" not in qs and parsed.hostname:
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port or 5432, socket.AF_INET)
            if infos:
                ip = infos[0][4][0]
                qs["hostaddr"] = [ip]
        except Exception:
            pass

    # Neon pooler requires endpoint id in options when SNI unsupported
    if parsed.hostname and "neon.tech" in parsed.hostname:
        host = parsed.hostname
        if host.startswith("ep-"):
            endpoint_id = host.split(".", 1)[0]
            options = qs.get("options", [])
            if not any("endpoint=" in opt for opt in options):
                options.append(f"endpoint={endpoint_id}")
                qs["options"] = options

    # Force IPv4 by replacing hostname in netloc if we resolved one
    if parsed.hostname and "hostaddr" in qs and qs["hostaddr"]:
        host_ipv4 = qs["hostaddr"][0]
        if host_ipv4:
            netloc = parsed.netloc
            # Replace hostname portion, preserving userinfo and port
            if "@" in netloc:
                userinfo, hostport = netloc.split("@", 1)
                host = hostport.split(":")[0]
                port = hostport.split(":")[1] if ":" in hostport else ""
                hostport_new = f"{host_ipv4}:{port}" if port else host_ipv4
                netloc = f"{userinfo}@{hostport_new}"
            else:
                host = netloc.split(":")[0]
                port = netloc.split(":")[1] if ":" in netloc else ""
                netloc = f"{host_ipv4}:{port}" if port else host_ipv4
            parsed = parsed._replace(netloc=netloc)

    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def get_conn():
    backend, target = _get_backend()
    if backend == "postgres":
        if psycopg is not None:
            return psycopg.connect(target)
        if psycopg2 is not None:
            return psycopg2.connect(target)
        raise RuntimeError("driver Postgres non installato")
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    backend, _ = _get_backend()
    conn = get_conn()
    cur = conn.cursor()
    if backend == "postgres":
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
                id SERIAL PRIMARY KEY,
                user_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                dataset_hash TEXT NOT NULL,
                pairwise_matrix_json TEXT NOT NULL,
                weights_json TEXT NOT NULL,
                cr DOUBLE PRECISION NOT NULL,
                UNIQUE(user_name, dataset_hash)
            );
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                dataset_hash TEXT NOT NULL,
                pairwise_matrix_json TEXT NOT NULL,
                weights_json TEXT NOT NULL,
                cr REAL NOT NULL,
                UNIQUE(user_name, dataset_hash)
            );
            """
        )
    conn.commit()
    conn.close()


def save_vote(
    user_name: str,
    dataset_hash: str,
    pairwise_matrix_json: str,
    weights_json: str,
    cr: float,
    created_at: str,
) -> None:
    backend, _ = _get_backend()
    conn = get_conn()
    cur = conn.cursor()
    if backend == "postgres":
        cur.execute(
            """
            INSERT INTO votes (user_name, created_at, dataset_hash, pairwise_matrix_json, weights_json, cr)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_name, dataset_hash) DO UPDATE SET
                created_at=EXCLUDED.created_at,
                pairwise_matrix_json=EXCLUDED.pairwise_matrix_json,
                weights_json=EXCLUDED.weights_json,
                cr=EXCLUDED.cr;
            """,
            (user_name, created_at, dataset_hash, pairwise_matrix_json, weights_json, cr),
        )
    else:
        cur.execute(
            """
            INSERT INTO votes (user_name, created_at, dataset_hash, pairwise_matrix_json, weights_json, cr)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_name, dataset_hash) DO UPDATE SET
                created_at=excluded.created_at,
                pairwise_matrix_json=excluded.pairwise_matrix_json,
                weights_json=excluded.weights_json,
                cr=excluded.cr;
            """,
            (user_name, created_at, dataset_hash, pairwise_matrix_json, weights_json, cr),
        )
    conn.commit()
    conn.close()


def fetch_votes(dataset_hash: str) -> List[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    if isinstance(conn, sqlite3.Connection):
        cur.execute(
            "SELECT user_name, pairwise_matrix_json, weights_json, cr FROM votes WHERE dataset_hash = ?",
            (dataset_hash,),
        )
    else:
        cur.execute(
            "SELECT user_name, pairwise_matrix_json, weights_json, cr FROM votes WHERE dataset_hash = %s",
            (dataset_hash,),
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def parse_vote_matrices(rows: List[Tuple]) -> List:
    matrices = []
    for _, matrix_json, _, _ in rows:
        matrices.append(matrix_from_json(matrix_json))
    return matrices


def parse_vote_weights(rows: List[Tuple]) -> List[dict]:
    weights = []
    for _, _, weights_json, _ in rows:
        weights.append(json.loads(weights_json))
    return weights
