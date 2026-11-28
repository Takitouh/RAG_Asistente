#!/usr/bin/env python3
"""Script de restauración de base de datos a la versión anterior (Iteración 1).

Restaura el respaldo SQLite tomado antes de la migración de la Etapa 1.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from normativa.config import settings


def restore(backup_file: Path | str | None = None) -> None:
    target_path = Path(settings.SQLITE_PATH)
    backup_dir = PROJECT_ROOT / "data" / "backups"

    if backup_file:
        src = Path(backup_file)
    else:
        # Buscar el respaldo de referencia
        src = backup_dir / "normativa_backup_iteracion_01.db"

    if not src.exists():
        print(f"Error: No se encontró el archivo de respaldo: {src}")
        sys.exit(1)

    print(f"Restaurando {src} -> {target_path}...")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, target_path)
    print("Restauración completada con éxito.")


if __name__ == "__main__":
    bf = sys.argv[1] if len(sys.argv) > 1 else None
    restore(bf)
