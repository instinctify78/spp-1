from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api import runs, system

# Create all tables on startup (Alembic handles migrations in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SPP-1 LLM GPU Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router, prefix="/runs", tags=["runs"])
app.include_router(system.router, prefix="/system", tags=["system"])


@app.get("/health")
def health():
    return {"status": "ok"}
