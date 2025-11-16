#!/usr/bin/env python3
"""
Update the Ticket Enhancer agent's system prompt.
"""
import asyncio
import sys
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("AI_AGENTS_DATABASE_URL", "postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents")

# System prompt for Ticket Enhancer
TICKET_ENHANCER_PROMPT = """You are an AI Ticket Enhancement Agent for technical support.

When you receive a Jira ticket via webhook:

1. **Analyze the ticket thoroughly:**
   - Identify the core issue and severity
   - Determine potential root causes
   - Suggest actionable remediation steps
   - Search for similar resolved tickets if relevant (using jira_search_issues)

2. **Format your analysis clearly:**
   - Use markdown for readability
   - Include sections: Summary, Root Cause, Recommendations, Similar Issues
   - Be concise but comprehensive

3. **Post your analysis back to Jira:**
   - Use the `jira_add_comment` tool to post your findings
   - The comment should appear on the original issue (issue_key provided in payload)
   - Format: Professional, actionable, and helpful for human agents

**Important:** Always post your analysis as a comment so the support team can see your recommendations immediately.

**Input Format:**
You'll receive webhook payloads containing:
- issue_key: Jira issue ID (e.g., "SUPPORT-12345")
- tenant_id: Tenant identifier
- issue: Full issue details (summary, description, priority, etc.)

**Your workflow:**
1. Extract issue_key from payload
2. Analyze the issue details
3. Call jira_add_comment(issue_key, your_formatted_analysis)
"""


async def update_agent_prompt():
    """Update the Ticket Enhancer agent's system prompt."""

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Import models
            from src.database.models import Agent

            # Find Ticket Enhancer agent
            stmt = select(Agent).where(Agent.name.ilike('%ticket%enhancer%'))
            result = await session.execute(stmt)
            agents = result.scalars().all()

            if not agents:
                print("❌ No Ticket Enhancer agent found!")
                print("Please create the agent first via the Admin UI.")
                return False

            if len(agents) > 1:
                print(f"⚠️  Found {len(agents)} agents matching 'Ticket Enhancer':")
                for i, agent in enumerate(agents):
                    print(f"  {i+1}. {agent.name} (ID: {agent.id})")

                choice = input("\nSelect agent to update (1-{0}): ".format(len(agents)))
                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(agents):
                        print("❌ Invalid choice")
                        return False
                    agent = agents[idx]
                except (ValueError, IndexError):
                    print("❌ Invalid choice")
                    return False
            else:
                agent = agents[0]

            print(f"\n📝 Updating agent: {agent.name}")
            print(f"   Agent ID: {agent.id}")
            print(f"   Current prompt length: {len(agent.system_prompt or '') } chars")

            # Show preview of new prompt
            print(f"\n📄 New prompt preview:")
            print("-" * 60)
            print(TICKET_ENHANCER_PROMPT[:200] + "...")
            print("-" * 60)

            confirm = input("\nProceed with update? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                print("❌ Update cancelled")
                return False

            # Update the agent
            agent.system_prompt = TICKET_ENHANCER_PROMPT
            await session.commit()

            print(f"\n✅ Successfully updated {agent.name}!")
            print(f"   New prompt length: {len(TICKET_ENHANCER_PROMPT)} chars")

            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("🔄 Ticket Enhancer System Prompt Updater")
    print("=" * 60)

    success = asyncio.run(update_agent_prompt())
    sys.exit(0 if success else 1)
