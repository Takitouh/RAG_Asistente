# normativa-tg

## Levantar el entorno

```bash
uv sync
docker compose up -d
uv run uvicorn normativa.api.main:app --port 8000
```

## Verificación

```bash
uv run pytest
uv run python scripts/check_env.py
```

