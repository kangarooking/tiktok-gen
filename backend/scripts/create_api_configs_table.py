#!/usr/bin/env python
"""
Database Migration: Create user_api_configs table

This script creates the user_api_configs table if it doesn't exist.
Run this after deploying the new API configuration feature.

Usage:
    python scripts/create_api_configs_table.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.database import engine, Base
from app.models.user_api_config import UserApiConfig  # Import to register the model


def create_api_configs_table():
    """Create user_api_configs table"""

    print("Creating user_api_configs table...")

    # Check if table already exists
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'user_api_configs')"
        ))
        exists = result.scalar()

        if exists:
            print("Table 'user_api_configs' already exists.")
            return

    # Create the table
    UserApiConfig.__table__.create(engine, checkfirst=True)

    print("✓ Table 'user_api_configs' created successfully!")
    print("\nTable structure:")
    print("  - id: UUID (Primary Key)")
    print("  - user_id: UUID (Nullable, FK to users)")
    print("  - category: String(30)")
    print("  - provider: String(50)")
    print("  - config_data: Text (Encrypted JSON)")
    print("  - display_name: String(100)")
    print("  - is_active: Boolean")
    print("  - is_default: Boolean")
    print("  - is_system: Boolean")
    print("  - is_validated: Boolean")
    print("  - last_validated_at: DateTime")
    print("  - validation_error: Text")
    print("  - created_at: DateTime")
    print("  - updated_at: DateTime")
    print("\nConstraints:")
    print("  - Unique: (user_id, category, provider)")


if __name__ == "__main__":
    create_api_configs_table()
