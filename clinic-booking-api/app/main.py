"""Application entry point: wires settings, database, error handling, key check and routers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.config import load_settings
from app.errors import install_error_handlers
from app.routers import health, reset, slots
from app.security import api_key_middleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Settings are read at startup (not at import) so `import app.main` works without them.
    settings = load_settings()
    app.state.settings = settings
    db.run_migrations(settings.database_url)
    db.init_pool(settings.database_url)
    try:
        yield
    finally:
        db.close_pool()


app = FastAPI(title="Clinic booking API", version="1.0", lifespan=lifespan)
install_error_handlers(app)
app.middleware("http")(api_key_middleware)
app.include_router(health.router)
app.include_router(slots.router)
app.include_router(reset.router)
