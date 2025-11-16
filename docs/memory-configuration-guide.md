# Memory Configuration Guide

**Story 8.15: Memory Configuration UI**
**Version**: 1.0
**Last Updated**: 2025-11-07

## Table of Contents

1. [Overview](#overview)
2. [Memory Types](#memory-types)
3. [Configuration Options](#configuration-options)
4. [API Reference](#api-reference)
5. [LangGraph Integration](#langgraph-integration)
6. [pgvector Setup](#pgvector-setup)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The AI Agents platform implements a three-tier memory system for agent context persistence:

- **Short-Term Memory**: Conversation history within a single session (PostgresSaver checkpointer)
- **Long-Term Memory**: Semantic memory across sessions with vector similarity search (pgvector)
- **Agentic Memory**: Agent-managed structured notes extracted during execution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Execution Layer                     │
│  (LangGraph Workflow with Memory Integration)               │
└────────────┬──────────────────────────┬─────────────────────┘
             │                          │
             ▼                          ▼
   ┌─────────────────┐       ┌──────────────────┐
   │ PostgresSaver   │       │ MemoryConfig     │
   │ (Checkpointer)  │       │ Service          │
   │                 │       │                  │
   │ Short-Term      │       │ Long-Term +      │
   │ Conversation    │       │ Agentic Memory   │
   └─────────────────┘       └──────────────────┘
             │                          │
             │                          ▼
             │                ┌──────────────────┐
             │                │ EmbeddingService │
             │                │ (OpenAI)         │
             │                └──────────────────┘
             │                          │
             └──────────┬───────────────┘
                        ▼
             ┌─────────────────────┐
             │   PostgreSQL +      │
             │   pgvector          │
             │                     │
             │ - agent_memory      │
             │ - checkpoints       │
             └─────────────────────┘
```

## Memory Types

### 1. Short-Term Memory (Conversation History)

**Purpose**: Maintains recent conversation context within a single session

**Implementation**: LangGraph PostgresSaver checkpointer with thread-based isolation

**Configuration**:
- `context_window_size`: Max tokens in context (512-128000, default: 4096)
- `conversation_history_length`: Max messages to retain (1-100, default: 10)

**Example**:
```json
{
  "short_term": {
    "context_window_size": 4096,
    "conversation_history_length": 10
  }
}
```

**Use Cases**:
- Multi-turn conversations
- Context carryover within a session
- Recent interaction recall

### 2. Long-Term Memory (Semantic Memory)

**Purpose**: Persistent semantic memory across sessions with vector similarity search

**Implementation**: PostgreSQL pgvector with OpenAI embeddings (text-embedding-3-small, 1536 dims)

**Configuration**:
- `enabled`: Enable/disable long-term memory (default: True)
- `vector_db`: Database backend ("postgresql_pgvector", default)
- `retention_days`: Days before auto-deletion (1-3650, default: 90)

**Example**:
```json
{
  "long_term": {
    "enabled": true,
    "vector_db": "postgresql_pgvector",
    "retention_days": 90
  }
}
```

**Use Cases**:
- User preference recall
- Historical context retrieval
- Personalized responses
- Knowledge accumulation

### 3. Agentic Memory (Structured Notes)

**Purpose**: Agent-managed structured facts extracted during execution

**Implementation**: Agent autonomously extracts facts and stores as structured notes

**Configuration**:
- `enabled`: Enable/disable agentic memory (default: False)
- `retention_days`: Days before auto-deletion (1-3650, default: 90)

**Example**:
```json
{
  "agentic": {
    "enabled": false,
    "retention_days": 90
  }
}
```

**Use Cases**:
- Automatic fact extraction
- Structured knowledge graphs
- Agent-curated information

## Configuration Options

### Admin UI Configuration

Access memory configuration through the **Agent Management** page:

1. Navigate to **05_Agent_Management.py**
2. Select an agent
3. Click **Memory** tab
4. Configure memory settings:
   - Short-term: Context window size, history length
   - Long-term: Enable/disable, vector DB, retention
   - Agentic: Enable/disable, retention
5. Click **Save Memory Configuration**

### API Configuration

#### Get Memory Configuration

```bash
GET /api/agents/{agent_id}/memory/config
```

**Response**:
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "config": {
    "short_term": {
      "context_window_size": 4096,
      "conversation_history_length": 10
    },
    "long_term": {
      "enabled": true,
      "vector_db": "postgresql_pgvector",
      "retention_days": 90
    },
    "agentic": {
      "enabled": false,
      "retention_days": 90
    }
  },
  "created_at": "2025-11-07T10:00:00Z",
  "updated_at": "2025-11-07T10:00:00Z"
}
```

#### Update Memory Configuration

```bash
PUT /api/agents/{agent_id}/memory/config
Content-Type: application/json

{
  "short_term": {
    "context_window_size": 8192,
    "conversation_history_length": 20
  }
}
```

**Response**: Updated configuration

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{agent_id}/memory/config` | GET | Get memory configuration |
| `/api/agents/{agent_id}/memory/config` | PUT | Update memory configuration |
| `/api/agents/{agent_id}/memory/state` | GET | Get current memory state |
| `/api/agents/{agent_id}/memory` | DELETE | Clear agent memory |
| `/api/agents/{agent_id}/memory/history` | GET | Get paginated memory history |

### Authentication

All endpoints require tenant authentication via `get_tenant_id()` dependency.

**Headers**:
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>
```

### Clear Memory

```bash
DELETE /api/agents/{agent_id}/memory?memory_type=long_term
```

**Query Parameters**:
- `memory_type`: Optional filter (`short_term`, `long_term`, `agentic`, or omit for all)

**Response**:
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "cleared_count": 15,
  "memory_type": "long_term",
  "cleared_at": "2025-11-07T10:00:00Z"
}
```

## LangGraph Integration

### Checkpointer Pattern (Short-Term Memory)

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.services.langgraph_memory import LangGraphMemoryIntegration

# Initialize memory integration
memory_integration = LangGraphMemoryIntegration(db)

# Get checkpointer
checkpointer = await memory_integration.get_checkpointer(agent_id)

# Compile graph with checkpointer
graph = builder.compile(checkpointer=checkpointer)

# Execute with thread ID for conversation isolation
config = {
    "configurable": {
        "thread_id": memory_integration.get_thread_id(agent_id)
    }
}

result = await graph.ainvoke({"messages": user_input}, config)
```

### Load Memory at Execution Start

```python
from src.services.langgraph_memory import LangGraphMemoryIntegration

memory_integration = LangGraphMemoryIntegration(db)

# Load relevant memories
memory_context = await memory_integration.load_agent_memory(
    agent_id=agent_id,
    tenant_id=tenant_id,
    query_text="User input for semantic search"
)

# Format for LLM prompt
memory_prompt = await memory_integration.format_memory_for_prompt(memory_context)

# Add to system messages
system_message = f"""
You are an AI agent with the following relevant memories:

{memory_prompt}

Use these memories to inform your response.
"""
```

### Save Memory After Execution

```python
# Extract new messages from agent execution
new_messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]

# Save memories (with optional fact extraction)
saved_count = await memory_integration.save_agent_memory(
    agent_id=agent_id,
    tenant_id=tenant_id,
    new_messages=new_messages,
    extract_facts=True  # Enable long-term memory extraction
)
```

## pgvector Setup

### Installation

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Vector Similarity Search

The `agent_memory` table uses pgvector for semantic search:

```sql
-- Table structure
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    memory_type VARCHAR(20) NOT NULL,
    content JSONB NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    retention_days INT DEFAULT 90,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector index for fast similarity search
CREATE INDEX idx_agent_memory_embedding
ON agent_memory USING ivfflat (embedding vector_cosine_ops);
```

### Cosine Similarity Query

```python
from sqlalchemy import text, select
from src.database.models import AgentMemory

# Generate query embedding
query_embedding = await embedding_service.generate_embedding(query_text)

# Cosine distance search (lower distance = higher similarity)
stmt = (
    select(AgentMemory)
    .where(AgentMemory.agent_id == agent_id)
    .order_by(text(f"embedding <-> '{query_embedding}'::vector"))
    .limit(5)
)

result = await db.execute(stmt)
memories = result.scalars().all()
```

## Best Practices

### 1. Retention Policy Configuration

- **Short-term**: Keep 7-30 days for debugging
- **Long-term**: 90-365 days for user preferences
- **Agentic**: Match long-term retention

### 2. Context Window Sizing

- **Small models (GPT-3.5)**: 4096 tokens
- **Large models (GPT-4)**: 8192-16384 tokens
- **Very large models (Claude 3)**: 32768+ tokens

### 3. Embedding Cost Optimization

- Enable Redis caching (7-day TTL)
- Batch embed multiple texts when possible
- Generate embeddings async to avoid blocking

### 4. Memory Cleanup

- Runs daily at 2:00 AM UTC via Celery Beat
- Manual cleanup: `DELETE /api/agents/{agent_id}/memory`
- Monitor memory growth in admin dashboard

### 5. Semantic Search Quality

- Use descriptive query text for better retrieval
- Limit results to 5-10 most relevant memories
- Consider similarity score threshold (0.7+)

## Troubleshooting

### Issue: Embeddings Not Generated

**Symptoms**: Long-term memories have `null` embeddings

**Solutions**:
1. Check OpenAI API key: `AI_AGENTS_OPENAI_API_KEY`
2. Verify Redis connection for caching
3. Review logs for rate limit errors
4. Test embedding service manually:
   ```python
   from src.services.embedding_service import EmbeddingService

   service = EmbeddingService()
   embedding = await service.generate_embedding("Test text")
   print(f"Embedding dims: {len(json.loads(embedding))}")
   ```

### Issue: Checkpointer Connection Fails

**Symptoms**: `Failed to initialize checkpointer` error

**Solutions**:
1. Verify database URL: `AI_AGENTS_DATABASE_URL`
2. Check PostgreSQL connection pooling
3. Ensure `asyncpg` driver installed
4. Review database logs for connection errors

### Issue: Memory Not Cleared

**Symptoms**: Memories persist after deletion

**Solutions**:
1. Verify tenant ID matches agent
2. Check foreign key cascade rules
3. Review retention policy query logic
4. Manual cleanup via psql:
   ```sql
   DELETE FROM agent_memory
   WHERE agent_id = '<uuid>'
   AND tenant_id = '<tenant>';
   ```

### Issue: Vector Search Returns Irrelevant Results

**Symptoms**: Low similarity scores or wrong memories retrieved

**Solutions**:
1. Regenerate embeddings with updated model
2. Increase result limit to get more candidates
3. Filter by memory_type for specific searches
4. Review content quality in stored memories

## Monitoring & Analytics

### Memory Metrics

Track in admin dashboard:
- Total memories per agent
- Memories by type (short-term, long-term, agentic)
- Oldest/newest memory timestamps
- Retention policy cleanup counts

### Celery Beat Schedule

```python
# celeryconfig.py
from celery.schedules import crontab

beat_schedule = {
    'cleanup-expired-memories': {
        'task': 'cleanup_expired_memories',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM UTC
    },
}
```

## References

- [LangGraph Checkpointer Docs](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Story 8.15 Specification](./stories/8-15-memory-configuration-ui.md)
