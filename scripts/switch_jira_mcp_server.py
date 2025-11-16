#!/usr/bin/env python3
"""
Script to switch from faulty sooperset/mcp-atlassian to fkesheh/jira-mcp-server
with Jira API v3 support.

This addresses the API deprecation issue where the old MCP server uses
/rest/api/2/search (removed by Atlassian) instead of /rest/api/3/search/jql.
"""

import asyncio
import json
import os
from uuid import UUID

import asyncpg
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Database connection URL
DATABASE_URL = os.getenv("AI_AGENTS_DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://aiagents:password@localhost:5432/ai_agents"

# MCP Server details
MCP_SERVER_ID = UUID("77ee99f6-8f9f-4d24-aba7-830146e06c0e")
TENANT_ID = "test1"

# Jira credentials from environment
JIRA_URL = os.getenv("JIRA_URL", "https://aiopstest1.atlassian.net")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "effect-datum8k@icloud.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# New MCP server configuration (fkesheh/jira-mcp-server)
# Using npx to run without installation
NEW_CONFIG = {
    "name": "Jira Cloud MCP (API v3)",
    "description": "Jira MCP server with API v3 support - replaces deprecated sooperset/mcp-atlassian",
    "transport_type": "stdio",
    "command": "npx",
    "args": [
        "-y",  # Auto-accept installation
        "@fkesheh/jira-mcp-server@latest"
    ],
    "env": {
        "JIRA_URL": JIRA_URL,
        "JIRA_USERNAME": JIRA_USERNAME,
        "JIRA_API_TOKEN": JIRA_API_TOKEN,
        "JIRA_API_VERSION": "3"  # CRITICAL: Use API v3
    }
}


async def update_mcp_server():
    """Update the MCP server configuration in the database."""

    # Convert asyncpg URL (asyncpg:// -> postgres://)
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)

    try:
        # Update the MCP server configuration
        await conn.execute(
            """
            UPDATE mcp_servers
            SET
                name = $1,
                description = $2,
                transport_type = $3,
                command = $4,
                args = $5,
                env = $6,
                status = 'pending',
                error_message = NULL,
                consecutive_failures = 0,
                updated_at = NOW()
            WHERE id = $7 AND tenant_id = $8
            """,
            NEW_CONFIG["name"],
            NEW_CONFIG["description"],
            NEW_CONFIG["transport_type"],
            NEW_CONFIG["command"],
            json.dumps(NEW_CONFIG["args"]),
            json.dumps(NEW_CONFIG["env"]),
            MCP_SERVER_ID,
            TENANT_ID
        )

        print(f"✅ Successfully updated MCP server {MCP_SERVER_ID}")
        print(f"\nNew Configuration:")
        print(f"  Name: {NEW_CONFIG['name']}")
        print(f"  Command: {NEW_CONFIG['command']}")
        print(f"  Args: {' '.join(NEW_CONFIG['args'])}")
        print(f"  Jira API Version: {NEW_CONFIG['env']['JIRA_API_VERSION']}")

        # Verify update
        row = await conn.fetchrow(
            "SELECT name, command, args, env, status FROM mcp_servers WHERE id = $1",
            MCP_SERVER_ID
        )

        if row:
            print(f"\n✅ Verification:")
            print(f"  Database name: {row['name']}")
            print(f"  Database command: {row['command']}")
            print(f"  Status: {row['status']}")

            env_data = json.loads(row['env'])
            print(f"  API Version: {env_data.get('JIRA_API_VERSION', 'NOT SET')}")

    finally:
        await conn.close()


async def main():
    """Main execution."""
    print("=" * 80)
    print("Switching Jira MCP Server to fkesheh/jira-mcp-server with API v3 support")
    print("=" * 80)
    print()

    if not JIRA_API_TOKEN:
        print("⚠️  WARNING: JIRA_API_TOKEN not found in environment")
        print("   The script will continue but the token will be empty")
        print()

    await update_mcp_server()

    print()
    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("1. Restart the worker to load new configuration:")
    print("   docker-compose restart worker")
    print()
    print("2. Test the connection via Streamlit UI:")
    print("   - Navigate to MCP Servers page")
    print("   - Click 'Test Connection' on Jira Cloud MCP (API v3)")
    print()
    print("3. Trigger a test ticket enhancement to verify tools work:")
    print("   ./test_ticket_enhancer_real.sh")
    print()


if __name__ == "__main__":
    asyncio.run(main())
