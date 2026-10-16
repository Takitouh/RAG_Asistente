from fastapi import FastAPI


app = FastAPI(title="Normativa TG")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

