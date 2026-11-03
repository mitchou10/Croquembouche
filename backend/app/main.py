from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import KeycloakSettings
from app.routers.analyses import router as analyses_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.internal import router as internal_router
from app.routers.reference import router as reference_router
from app.routers.templates import router as templates_router

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
app.include_router(documents_router, prefix="/api/documents")
app.include_router(templates_router, prefix="/api/templates")
app.include_router(analyses_router, prefix="/api/analyses")
app.include_router(reference_router, prefix="/api")
app.include_router(internal_router, prefix="/internal")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
