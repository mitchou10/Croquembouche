from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import KeycloakSettings
from app.routers.auth import router as auth_router

app = FastAPI(title="Croquembouche")

# The browser calls the API from the frontend's origin, with the session cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[KeycloakSettings().FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
