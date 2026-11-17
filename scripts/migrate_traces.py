#!/usr/bin/env python3
"""Migración: añade las columnas nuevas a la tabla traces si no existen.

Ejecutar UNA sola vez:
    python scripts/migrate_traces.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/normativa.db")

NEW_COLUMNS = [
    ("citations_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("abstention_reason", "TEXT"),
    ("retrieval_ms", "REAL NOT NULL DEFAULT 0.0"),
    ("generation_ms", "REAL NOT NULL DEFAULT 0.0"),
    ("total_ms", "REAL NOT NULL DEFAULT 0.0"),
    ("execution_status", "TEXT NOT NULL DEFAULT 'ok'"),
    ("error_message", "TEXT"),
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Base de datos no encontrada en {DB_PATH}. Nada que migrar.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(traces)")}

    added = []
    for col_name, col_def in NEW_COLUMNS:
        if col_name not in existing:
            cur.execute(f"ALTER TABLE traces ADD COLUMN {col_name} {col_def}")
            added.append(col_name)

    conn.commit()
    conn.close()

    if added:
        print(f"Columnas añadidas a 'traces': {added}")
    else:
        print("La tabla 'traces' ya tiene todas las columnas requeridas.")


if __name__ == "__main__":
    main()
