from fastapi import FastAPI

app = FastAPI(title="Croquembouche")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
