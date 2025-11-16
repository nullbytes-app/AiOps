#!/usr/bin/env python3
"""
Migration script to fix tenants missing LiteLLM virtual keys (Story 8.9).

This script:
1. Identifies tenants without litellm_virtual_key
2. Generates virtual key via LiteLLM API
3. Encrypts and stores key in database
4. Logs audit trail

Run from project root:
    python scripts/fix_missing_virtual_keys.py

Or via Docker:
    docker-compose exec api python scripts/fix_missing_virtual_keys.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def fix_missing_virtual_keys():
    """Fix all tenants missing virtual keys."""
    from sqlalchemy import select
    from src.database.models import TenantConfig
    from src.database.session import get_async_session
    from src.services.llm_service import LLMService
    from src.utils.encryption import encrypt

    print("=" * 80)
    print("LiteLLM Virtual Key Migration - Story 8.9")
    print("=" * 80)
    print()

    async for db in get_async_session():
        try:
            llm_service = LLMService(db=db)

            # Find tenants without virtual keys
            stmt = select(TenantConfig).where(
                TenantConfig.is_active == True,
                TenantConfig.litellm_virtual_key == None,
            )
            result = await db.execute(stmt)
            tenants_missing_keys = list(result.scalars().all())

            if not tenants_missing_keys:
                print("✅ All active tenants have virtual keys configured!")
                print()
                return

            print(f"Found {len(tenants_missing_keys)} tenant(s) missing virtual keys:")
            for tenant in tenants_missing_keys:
                print(f"  - {tenant.tenant_id} ({tenant.name})")
            print()

            # Confirm migration
            confirm = input("Generate virtual keys for these tenants? [y/N]: ")
            if confirm.lower() != "y":
                print("❌ Migration cancelled.")
                return

            print()
            print("Generating virtual keys...")
            print()

            success_count = 0
            failed_count = 0

            for tenant in tenants_missing_keys:
                try:
                    print(f"Processing {tenant.tenant_id}...")

                    # Generate virtual key via LiteLLM
                    virtual_key = await llm_service.create_virtual_key_for_tenant(
                        tenant_id=tenant.tenant_id,
                        max_budget=100.0,  # Default $100 budget
                    )

                    # Encrypt and store in database
                    tenant.litellm_virtual_key = encrypt(virtual_key)
                    tenant.litellm_key_created_at = datetime.now(timezone.utc)
                    await db.flush()
                    await db.refresh(tenant)

                    # Log audit entry
                    await llm_service.log_audit_entry(
                        operation="llm_key_created_migration",
                        tenant_id=tenant.tenant_id,
                        user="migration_script",
                        details={
                            "max_budget": 100.0,
                            "key_alias": f"{tenant.tenant_id}-key",
                            "reason": "Story 8.9 migration for existing tenant",
                        },
                        status="success",
                    )

                    print(f"  ✅ Virtual key created for {tenant.tenant_id}")
                    success_count += 1

                except Exception as e:
                    print(f"  ❌ Failed to create key for {tenant.tenant_id}: {e}")
                    failed_count += 1
                    continue

            # Commit all changes
            await db.commit()

            print()
            print("=" * 80)
            print("Migration Summary:")
            print(f"  ✅ Success: {success_count}")
            print(f"  ❌ Failed: {failed_count}")
            print("=" * 80)
            print()

            if failed_count > 0:
                print("⚠️  Some tenants failed. Check logs for details.")
                sys.exit(1)
            else:
                print("✅ All tenants now have virtual keys!")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(fix_missing_virtual_keys())
