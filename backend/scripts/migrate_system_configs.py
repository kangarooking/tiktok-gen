#!/usr/bin/env python
"""
Migration Script: Import System API Configurations from .env

This script reads the existing .env configuration and imports
system-level API configurations into the database.

Run this script after database migration to populate initial configs:

    python scripts/migrate_system_configs.py

The script will:
1. Read settings from environment/.env
2. Create system-level configs (user_id=NULL, is_system=True)
3. Skip if configs already exist
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Set up Django-style settings before imports
os.chdir(backend_path)

from app.config import settings
from app.database import SessionLocal
from app.services.api_config_service import ApiConfigService
from app.core.provider_constants import ApiCategory


async def migrate_system_configs():
    """Import system configurations from .env to database"""

    db = SessionLocal()
    service = ApiConfigService(db)

    print("=" * 60)
    print("Migrating System API Configurations from .env")
    print("=" * 60)

    try:
        # ============================================================
        # LLM Configuration (GLM)
        # ============================================================
        print("\n[1/7] Migrating LLM Configuration (GLM)...")

        if settings.GLM_API_KEY:
            try:
                await service.create_system_config(
                    category=ApiCategory.LLM.value,
                    provider="glm",
                    config_data={
                        "api_key": settings.GLM_API_KEY,
                        "base_url": settings.GLM_API_URL,
                        "model": settings.GLM_MODEL,
                    },
                    display_name="GLM-4 (System Default)",
                    set_as_default=True
                )
                print("  ✓ GLM configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate GLM: {e}")
        else:
            print("  - GLM_API_KEY not set, skipping")

        # ============================================================
        # TTS Configuration (Index TTS)
        # ============================================================
        print("\n[2/7] Migrating TTS Configuration (Index TTS)...")

        if settings.INDEX_TTS_API_KEY and settings.INDEX_TTS_BASE_URL:
            try:
                await service.create_system_config(
                    category=ApiCategory.TTS.value,
                    provider="index_tts",
                    config_data={
                        "api_key": settings.INDEX_TTS_API_KEY,
                        "base_url": settings.INDEX_TTS_BASE_URL,
                        "timeout": settings.INDEX_TTS_TIMEOUT,
                    },
                    display_name="Index TTS 302 (System Default)",
                    set_as_default=True
                )
                print("  ✓ Index TTS configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate Index TTS: {e}")
        else:
            print("  - INDEX_TTS_API_KEY or INDEX_TTS_BASE_URL not set, skipping")

        # ============================================================
        # TTS Configuration (SiliconFlow)
        # ============================================================
        print("\n[3/7] Migrating TTS Configuration (SiliconFlow)...")

        if settings.SILICONFLOW_API_KEY and settings.SILICONFLOW_BASE_URL:
            try:
                await service.create_system_config(
                    category=ApiCategory.TTS.value,
                    provider="siliconflow_tts",
                    config_data={
                        "api_key": settings.SILICONFLOW_API_KEY,
                        "base_url": settings.SILICONFLOW_BASE_URL,
                        "model": settings.SILICONFLOW_TTS_MODEL,
                        "voice": settings.SILICONFLOW_TTS_VOICE,
                        "timeout": settings.SILICONFLOW_TTS_TIMEOUT,
                        "response_format": "mp3",
                    },
                    display_name="SiliconFlow TTS",
                    set_as_default=False
                )
                print("  ✓ SiliconFlow TTS configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate SiliconFlow TTS: {e}")
        else:
            print("  - SILICONFLOW_API_KEY or SILICONFLOW_BASE_URL not set, skipping")

        # ============================================================
        # Digital Human Configuration (WaveSpeed)
        # ============================================================
        print("\n[4/7] Migrating Digital Human Configuration (WaveSpeed)...")

        if settings.WAVESPEED_API_KEY:
            try:
                await service.create_system_config(
                    category=ApiCategory.DIGITAL_HUMAN.value,
                    provider="wavespeed",
                    config_data={
                        "api_key": settings.WAVESPEED_API_KEY,
                        "base_url": settings.WAVESPEED_API_BASE_URL,
                    },
                    display_name="WaveSpeed AI (System Default)",
                    set_as_default=True
                )
                print("  ✓ WaveSpeed configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate WaveSpeed: {e}")
        else:
            print("  - WAVESPEED_API_KEY not set, skipping")

        # ============================================================
        # Digital Human Configuration (Ark Seedance)
        # ============================================================
        print("\n[5/7] Migrating Digital Human Configuration (Ark Seedance)...")

        if settings.ARK_API_KEY:
            try:
                await service.create_system_config(
                    category=ApiCategory.DIGITAL_HUMAN.value,
                    provider="ark_seedance",
                    config_data={
                        "api_key": settings.ARK_API_KEY,
                        "base_url": settings.ARK_BASE_URL,
                        "model": settings.ARK_SEEDANCE_MODEL,
                        "duration": settings.ARK_SEEDANCE_DURATION,
                        "resolution": settings.ARK_SEEDANCE_RESOLUTION,
                        "aspect_ratio": settings.ARK_SEEDANCE_ASPECT_RATIO,
                        "watermark": settings.ARK_SEEDANCE_WATERMARK,
                        "camera_fixed": settings.ARK_SEEDANCE_CAMERA_FIXED,
                        "extra_flags": settings.ARK_SEEDANCE_EXTRA_FLAGS,
                        "timeout": settings.ARK_TIMEOUT,
                        "poll_interval": settings.ARK_POLL_INTERVAL_SECONDS,
                    },
                    display_name="VolcEngine Seedance",
                    set_as_default=False
                )
                print("  ✓ Ark Seedance configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate Ark Seedance: {e}")
        else:
            print("  - ARK_API_KEY not set, skipping")

        # ============================================================
        # Cloud Storage Configuration (Aliyun OSS)
        # ============================================================
        print("\n[6/7] Migrating Cloud Storage Configuration (Aliyun OSS)...")

        if settings.OSS_ACCESS_KEY_ID and settings.OSS_ACCESS_KEY_SECRET:
            try:
                await service.create_system_config(
                    category=ApiCategory.CLOUD_STORAGE.value,
                    provider="aliyun_oss",
                    config_data={
                        "access_key_id": settings.OSS_ACCESS_KEY_ID,
                        "access_key_secret": settings.OSS_ACCESS_KEY_SECRET,
                        "bucket_name": settings.OSS_BUCKET_NAME,
                        "endpoint": settings.OSS_ENDPOINT,
                        "region": settings.OSS_REGION,
                        "public_base_url": settings.OSS_PUBLIC_BASE_URL,
                    },
                    display_name="Aliyun OSS (System Default)",
                    set_as_default=True
                )
                print("  ✓ Aliyun OSS configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate Aliyun OSS: {e}")
        else:
            print("  - OSS credentials not set, skipping")

        # ============================================================
        # AI Image Configuration (Banana Pro)
        # Note: Currently hardcoded, need to add to .env
        # ============================================================
        print("\n[7/7] Migrating AI Image Configuration...")

        # Check for Banana Pro config (these might need to be added to .env)
        banana_api_key = getattr(settings, 'BANANA_PRO_API_KEY', None)
        banana_base_url = getattr(settings, 'BANANA_PRO_BASE_URL', 'https://api.banana.pro/v1')
        banana_model = getattr(settings, 'BANANA_PRO_MODEL', 'flux-pro')

        if banana_api_key:
            try:
                await service.create_system_config(
                    category=ApiCategory.AI_IMAGE.value,
                    provider="banana_pro",
                    config_data={
                        "api_key": banana_api_key,
                        "base_url": banana_base_url,
                        "model": banana_model,
                    },
                    display_name="Banana Pro (System Default)",
                    set_as_default=True
                )
                print("  ✓ Banana Pro configuration migrated")
            except Exception as e:
                print(f"  ✗ Failed to migrate Banana Pro: {e}")
        else:
            print("  - BANANA_PRO_API_KEY not set, skipping")
            print("    To add: Set BANANA_PRO_API_KEY in .env")

        print("\n" + "=" * 60)
        print("Migration Complete!")
        print("=" * 60)

        # Summary
        from app.models.user_api_config import UserApiConfig
        system_configs = db.query(UserApiConfig).filter(
            UserApiConfig.is_system == True
        ).count()

        print(f"\nTotal system configurations: {system_configs}")
        print("\nNote: System configs are used as fallbacks when users")
        print("don't have their own configurations configured.")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


def main():
    """Main entry point"""
    return asyncio.run(migrate_system_configs())


if __name__ == "__main__":
    sys.exit(main() or 0)
