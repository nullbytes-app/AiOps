#!/usr/bin/env python3
"""
Script to discover MCP tools from the Jira MCP server and update the database.
This manually triggers capability discovery that would normally happen via API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.mcp_stdio_client import MCPStdioClient
from src.schemas.mcp_server import MCPServerResponse
import asyncpg
from dotenv import load_dotenv
from uuid import UUID
from datetime import datetime, timezone

# Load environment
load_dotenv()

# Database connection URL
DATABASE_URL = os.getenv("AI_AGENTS_DATABASE_URL", "postgresql://aiagents:password@localhost:5432/ai_agents")

# MCP Server details
MCP_SERVER_ID = "77ee99f6-8f9f-4d24-aba7-830146e06c0e"
TENANT_ID = "test1"

# Jira credentials from environment
JIRA_URL = os.getenv("JIRA_URL", "https://aiopstest1.atlassian.net")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "effect-datum8k@icloud.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


async def discover_tools():
    """Discover tools from the MCP server."""

    print("=" * 80)
    print("Discovering MCP Tools from Jira MCP Server")
    print("=" * 80)
    print()

    # Create config object
    now = datetime.now(timezone.utc)
    config = MCPServerResponse(
        id=UUID(MCP_SERVER_ID),
        tenant_id=TENANT_ID,
        name="Jira Cloud MCP (API v3)",
        description="Test discovery",
        transport_type="stdio",
        command="npx",
        args=["-y", "@iflow-mcp/jira-mcp@latest"],
        env={
            "JIRA_URL": JIRA_URL,
            "JIRA_USERNAME": JIRA_USERNAME,
            "JIRA_API_TOKEN": JIRA_API_TOKEN,
        },
        status="active",
        discovered_tools=[],
        discovered_resources=[],
        discovered_prompts=[],
        created_at=now,
        updated_at=now
    )

    # Create MCP client
    client = MCPStdioClient(config=config)

    try:
        print("Starting MCP server...")
        await client.start()
        print("✅ MCP server started successfully")
        print()

        print("Discovering capabilities...")
        capabilities = await client.discover_capabilities()
        print(f"✅ Discovered {len(capabilities.get('tools', []))} tools")
        print(f"✅ Discovered {len(capabilities.get('resources', []))} resources")
        print(f"✅ Discovered {len(capabilities.get('prompts', []))} prompts")
        print()

        # Display tools
        tools = capabilities.get('tools', [])
        if tools:
            print("Tools discovered:")
            for tool in tools[:10]:  # Show first 10
                print(f"  - {tool.get('name')}: {tool.get('description', 'No description')[:60]}")
            if len(tools) > 10:
                print(f"  ... and {len(tools) - 10} more tools")
            print()

        # Convert asyncpg URL
        db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

        print("Updating database...")
        conn = await asyncpg.connect(db_url)

        try:
            # Update the MCP server with discovered capabilities
            await conn.execute(
                """
                UPDATE mcp_servers
                SET
                    discovered_tools = $1,
                    discovered_resources = $2,
                    discovered_prompts = $3,
                    status = 'active',
                    error_message = NULL,
                    last_health_check = NOW(),
                    updated_at = NOW()
                WHERE id = $4 AND tenant_id = $5
                """,
                json.dumps(tools),
                json.dumps(capabilities.get('resources', [])),
                json.dumps(capabilities.get('prompts', [])),
                MCP_SERVER_ID,
                TENANT_ID
            )

            print("✅ Database updated successfully")
            print()

            # Verify update
            row = await conn.fetchrow(
                """
                SELECT
                    name,
                    status,
                    jsonb_array_length(discovered_tools) as tool_count,
                    jsonb_array_length(discovered_resources) as resource_count
                FROM mcp_servers
                WHERE id = $1
                """,
                MCP_SERVER_ID
            )

            if row:
                print("Verification:")
                print(f"  Name: {row['name']}")
                print(f"  Status: {row['status']}")
                print(f"  Tools: {row['tool_count']}")
                print(f"  Resources: {row['resource_count']}")
                print()

        finally:
            await conn.close()

        print("=" * 80)
        print("SUCCESS! Tools discovered and database updated.")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Restart worker: docker-compose restart worker")
        print("2. Trigger test execution to verify agent has tools")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await client.stop()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(discover_tools())
    sys.exit(exit_code)
