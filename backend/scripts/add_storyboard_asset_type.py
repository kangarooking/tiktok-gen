#!/usr/bin/env python3
"""Add storyboard to the PostgreSQL asset_type enum.

Run from the repo root:
    PYTHONPATH=backend backend/.venv/bin/python backend/scripts/add_storyboard_asset_type.py
"""
from sqlalchemy import create_engine, text

from app.config import settings


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'storyboard'"))
    print("asset_type enum is ready for storyboard")


if __name__ == "__main__":
    main()
