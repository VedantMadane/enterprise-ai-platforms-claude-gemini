import os
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from meridian.config import CURRENT_ENV, SQLITE_PATH, DATA_DIR
from meridian.ingestion.directory_loader import load_directory
from meridian.ingestion.engine import IngestionEngine
from meridian.store.sqlite_store import SQLiteStore
from meridian.auth.rbac import RBACPolicy
from meridian.api.routes_usage import router as usage_router
from meridian.api.routes_admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    env_name = getattr(app.state, "env_name", None) or os.environ.get("MERIDIAN_ENV", "dev").lower()
    db_path = getattr(app.state, "db_path", None) or Path(os.environ.get("MERIDIAN_SQLITE_PATH", str(SQLITE_PATH)))
    
    # Initialize directory, store, and rbac engine
    directory = load_directory(DATA_DIR)
    store = SQLiteStore(db_path)
    
    # Run ingestion into SQLite if empty
    engine = IngestionEngine(DATA_DIR)
    _, records = engine.run_ingestion()
    store.seed_usage_records(records)
    
    # Seed capability defaults based on env_name
    group_ids = [g.group_id for g in directory.groups]
    store.seed_capabilities_from_env(env_name, group_ids)

    rbac = RBACPolicy(env_name)

    app.state.directory = directory
    app.state.store = store
    app.state.rbac = rbac
    yield

def create_app(env_name: Optional[str] = None, db_path: Optional[Path] = None) -> FastAPI:
    app = FastAPI(
        title="Meridian Life Sciences AI Platform — Usage & Admin Service",
        description="Unified usage ingestion, analytics API, and capability controls for Claude and Gemini",
        version="1.0.0",
        lifespan=lifespan
    )
    if env_name:
        app.state.env_name = env_name
    if db_path:
        app.state.db_path = db_path

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(usage_router)
    app.include_router(admin_router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        @app.get("/admin", include_in_schema=False)
        def serve_admin_ui():
            return FileResponse(static_dir / "index.html")

    return app

app = create_app()

def run():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("meridian.api.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
