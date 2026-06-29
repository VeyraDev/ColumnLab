from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("columnlab")


def run_migrations(database_url: str | None = None) -> None:
    backend_dir = Path(__file__).resolve().parent.parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")
    logger.info("Database migrations applied (alembic upgrade head)")
