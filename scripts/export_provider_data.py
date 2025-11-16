"""
Export Provider Data Before Dropping Tables

Story 9.2: Database Migration Preparation
Exports all llm_providers and llm_models data to JSON for backup.
"""

import json
import os
from datetime import datetime

from sqlalchemy import create_engine, text

# Get database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents",
)

# Convert async URL to sync for this script
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2")


def export_provider_data():
    """
    Export all provider data from database to JSON.

    Creates a backup file in data/backups/ directory.
    """
    engine = create_engine(DATABASE_URL)
    backup_dir = "data/backups"

    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)

    # Timestamp for backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/provider_backup_{timestamp}.json"

    backup_data = {"exported_at": datetime.now().isoformat(), "providers": [], "models": []}

    try:
        with engine.connect() as conn:
            # Check if tables exist
            tables_result = conn.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('llm_providers', 'llm_models')
                """
                )
            )
            tables = [row[0] for row in tables_result]

            if "llm_providers" not in tables and "llm_models" not in tables:
                print("✓ No provider tables found. Nothing to export.")
                return

            # Export providers
            if "llm_providers" in tables:
                providers_result = conn.execute(
                    text(
                        """
                    SELECT id, name, provider_type, api_base_url, api_key_encrypted,
                           enabled, created_at, updated_at, last_test_at, last_test_success
                    FROM llm_providers
                    ORDER BY id
                    """
                    )
                )

                for row in providers_result:
                    backup_data["providers"].append(
                        {
                            "id": row[0],
                            "name": row[1],
                            "provider_type": row[2],
                            "api_base_url": row[3],
                            "api_key_encrypted": row[4],
                            "enabled": row[5],
                            "created_at": str(row[6]),
                            "updated_at": str(row[7]),
                            "last_test_at": str(row[8]),
                            "last_test_success": row[9],
                        }
                    )

                print(f"✓ Exported {len(backup_data['providers'])} providers")

            # Export models
            if "llm_models" in tables:
                models_result = conn.execute(
                    text(
                        """
                    SELECT id, provider_id, model_name, display_name, context_window,
                           cost_per_input_token, cost_per_output_token, enabled, created_at
                    FROM llm_models
                    ORDER BY provider_id, id
                    """
                    )
                )

                for row in models_result:
                    backup_data["models"].append(
                        {
                            "id": row[0],
                            "provider_id": row[1],
                            "model_name": row[2],
                            "display_name": row[3],
                            "context_window": row[4],
                            "cost_per_input_token": float(row[5]) if row[5] else None,
                            "cost_per_output_token": float(row[6]) if row[6] else None,
                            "enabled": row[7],
                            "created_at": str(row[8]),
                        }
                    )

                print(f"✓ Exported {len(backup_data['models'])} models")

    except Exception as e:
        print(f"✗ Error exporting data: {str(e)}")
        return

    # Write backup file
    try:
        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=2)
        print(f"✓ Backup saved to: {backup_file}")
        print(f"\nTo restore this data later, you can reference:")
        print(f"  - File: {backup_file}")
        print(f"  - Providers: {len(backup_data['providers'])}")
        print(f"  - Models: {len(backup_data['models'])}")
    except Exception as e:
        print(f"✗ Error writing backup file: {str(e)}")


if __name__ == "__main__":
    print("Exporting LLM Provider data before dropping tables...")
    export_provider_data()
    print("\nDone!")
