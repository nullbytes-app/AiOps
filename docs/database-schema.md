# Database Schema Documentation

## Overview

The AI Agents Platform uses PostgreSQL with multi-tool support for different ticketing systems (ITSM tools). The schema supports ServiceDesk Plus, Jira Service Management, and future tools through a plugin architecture.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      tenant_configs                         │
├─────────────────────────────────────────────────────────────┤
│ PK  id                            UUID                      │
│ UK  tenant_id                     VARCHAR(100)              │
│     name                          VARCHAR(255)              │
│ IDX tool_type                     VARCHAR(50) = 'servicedesk_plus' │
│                                                               │
│     # ServiceDesk Plus fields (nullable)                    │
│     servicedesk_url               VARCHAR(500)              │
│     servicedesk_api_key_encrypted TEXT                      │
│                                                               │
│     # Jira fields (nullable)                                │
│     jira_url                      VARCHAR(500)              │
│     jira_api_token_encrypted      BYTEA                     │
│     jira_project_key              VARCHAR(50)               │
│                                                               │
│     # Common fields                                         │
│     webhook_signing_secret_encrypted TEXT                   │
│     enhancement_preferences       JSONB = '{}'::jsonb       │
│     rate_limits                   JSONB                     │
│     is_active                     BOOLEAN = TRUE            │
│     created_at                    TIMESTAMPTZ               │
│     updated_at                    TIMESTAMPTZ               │
└─────────────────────────────────────────────────────────────┘
```

## Table: tenant_configs

Primary table storing tenant configurations with multi-tool support.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| **id** | UUID | NOT NULL | uuid_generate_v4() | Primary key |
| **tenant_id** | VARCHAR(100) | NOT NULL | - | Unique tenant identifier (lowercase alphanumeric + hyphens) |
| **name** | VARCHAR(255) | NOT NULL | - | Human-readable tenant name |
| **tool_type** | VARCHAR(50) | NOT NULL | 'servicedesk_plus' | Plugin routing key (servicedesk_plus, jira, zendesk, etc.) |
| **servicedesk_url** | VARCHAR(500) | NULL | - | ServiceDesk Plus instance URL (required if tool_type='servicedesk_plus') |
| **servicedesk_api_key_encrypted** | TEXT | NULL | - | Fernet-encrypted API key for ServiceDesk Plus |
| **jira_url** | VARCHAR(500) | NULL | - | Jira Cloud instance URL (required if tool_type='jira') |
| **jira_api_token_encrypted** | BYTEA | NULL | - | Fernet-encrypted API token for Jira |
| **jira_project_key** | VARCHAR(50) | NULL | - | Default Jira project key (e.g., "SUPPORT") |
| **webhook_signing_secret_encrypted** | TEXT | NOT NULL | - | Fernet-encrypted webhook HMAC secret |
| **enhancement_preferences** | JSONB | NOT NULL | '{}'::jsonb | Tool-specific configuration (see JSONB Structure) |
| **rate_limits** | JSONB | NULL | Default rate limits | Per-tenant rate limiting config |
| **is_active** | BOOLEAN | NOT NULL | TRUE | Tenant active status |
| **created_at** | TIMESTAMPTZ | NOT NULL | now() | Creation timestamp |
| **updated_at** | TIMESTAMPTZ | NOT NULL | now() | Last update timestamp |

### Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| **tenant_configs_pkey** | id | PRIMARY KEY | Primary key uniqueness |
| **ix_tenant_configs_tenant_id** | tenant_id | UNIQUE BTREE | Unique tenant lookup |
| **idx_tenant_configs_tool_type** | tool_type | BTREE | Fast plugin routing (added in migration 3ad133f66494) |

### Row-Level Security (RLS)

- **Policy**: `tenant_config_isolation_policy`
- **Enforces**: Multi-tenancy isolation
- **Rule**: `tenant_id = current_setting('app.current_tenant_id')`
- **Effect**: Each tenant can only access their own configuration

## Enhancement Preferences JSONB Structure

The `enhancement_preferences` column stores tool-specific configuration as JSONB, enabling flexible schema per tool without database migrations.

### ServiceDesk Plus Example

```json
{
  "tool_config": {
    "default_category": "Network Issues",
    "default_priority": "High",
    "auto_assign_technician": "john.doe@company.com",
    "sla_policy_id": 12345
  },
  "priority_mapping": {
    "critical": "Urgent",
    "high": "High",
    "medium": "Medium",
    "low": "Low"
  },
  "custom_fields": {
    "department": "IT",
    "location": "Building A"
  }
}
```

### Jira Service Management Example

```json
{
  "tool_config": {
    "default_issue_type": "Bug",
    "default_project_key": "SUPPORT",
    "default_priority": "High",
    "auto_assign_user": "john.doe@company.com"
  },
  "priority_mapping": {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low"
  },
  "custom_fields": {
    "customfield_10000": "tenant-id-value",
    "customfield_10001": "escalation-tier-1"
  },
  "workflow_config": {
    "auto_transition_on_resolve": true,
    "target_status": "Resolved"
  }
}
```

### JSONB Query Examples

```sql
-- Get Jira default issue type for tenant
SELECT enhancement_preferences->'tool_config'->>'default_issue_type'
FROM tenant_configs
WHERE tenant_id = 'tenant-abc' AND tool_type = 'jira';

-- Filter tenants with specific priority mapping
SELECT tenant_id, name
FROM tenant_configs
WHERE enhancement_preferences @> '{"priority_mapping": {"critical": "Highest"}}'::jsonb;

-- Update tool config for specific tenant
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{tool_config,default_priority}',
    '"Medium"'
)
WHERE tenant_id = 'tenant-abc';
```

## Multi-Tool Support Pattern

### Tool-Specific Columns (Nullable Approach)

The schema uses **nullable tool-specific columns** rather than a pure JSONB approach to balance flexibility with type safety:

**Rationale:**
1. **Type safety**: VARCHAR/BYTEA columns enforce data types at DB level
2. **Performance**: Indexed tool_type enables fast plugin routing (<1ms)
3. **Schema clarity**: Explicit columns self-document supported tools
4. **Encryption**: BYTEA columns properly typed for encrypted credentials
5. **Flexibility**: enhancement_preferences JSONB handles tool-specific configs without schema changes
6. **Backward compatibility**: Nullable tool-specific columns preserve existing data

### Example Tenants

**ServiceDesk Plus Tenant:**
```sql
INSERT INTO tenant_configs (
    tenant_id, name, tool_type,
    servicedesk_url, servicedesk_api_key_encrypted,
    webhook_signing_secret_encrypted,
    enhancement_preferences
) VALUES (
    'acme-corp', 'Acme Corporation', 'servicedesk_plus',
    'https://acme.servicedesk.com',
    'encrypted_api_key_blob',
    'encrypted_webhook_secret',
    '{"tool_config": {"default_category": "Network"}}'::jsonb
);
```

**Jira Tenant:**
```sql
INSERT INTO tenant_configs (
    tenant_id, name, tool_type,
    jira_url, jira_api_token_encrypted, jira_project_key,
    webhook_signing_secret_encrypted,
    enhancement_preferences
) VALUES (
    'globex-inc', 'Globex Inc', 'jira',
    'https://globex.atlassian.net',
    '\xencrypted_token_bytes',
    'SUPPORT',
    'encrypted_webhook_secret',
    '{"tool_config": {"default_issue_type": "Bug"}}'::jsonb
);
```

### Query Patterns

**Find all Jira tenants:**
```sql
SELECT tenant_id, name, jira_url, jira_project_key
FROM tenant_configs
WHERE tool_type = 'jira';
-- Uses idx_tenant_configs_tool_type index
```

**Multi-tool tenant count:**
```sql
SELECT tool_type, COUNT(*) as tenant_count
FROM tenant_configs
GROUP BY tool_type;
```

## Migration History

### Migration 3ad133f66494 (2025-11-05)
**Story:** 7.3 - Migrate ServiceDesk Plus to Plugin Architecture

**Changes:**
- Added `tool_type` column (VARCHAR 50, NOT NULL, default 'servicedesk_plus')
- Created `idx_tenant_configs_tool_type` B-tree index

**Purpose:** Enable plugin routing for multi-tool support

### Migration 002217a1f0a8 (2025-11-05)
**Story:** 7.4 - Implement Jira Service Management Plugin

**Changes:**
- Added `jira_url` (VARCHAR 500, nullable)
- Added `jira_api_token_encrypted` (BYTEA, nullable)
- Added `jira_project_key` (VARCHAR 50, nullable)

**Purpose:** Support Jira Service Management tenants

### Migration Rollback

Both migrations support clean downgrade:
```bash
# Downgrade Jira fields
alembic downgrade -1  # Removes jira_* columns

# Downgrade tool_type
alembic downgrade -1  # Removes tool_type column and index
```

## Data Validation Rules

### Application-Level Validation

1. **tool_type must match registered plugin**
   - Validated by `TenantService.create_tenant()` via `PluginManager.get_plugin()`
   - Raises `PluginNotFoundError` if plugin not registered
   - Dynamic plugin registration makes DB CHECK constraint inflexible

2. **Required fields per tool_type**
   - Validated by Pydantic `@model_validator` in `TenantConfigCreate`
   - ServiceDesk Plus: `servicedesk_url`, `servicedesk_api_key` required
   - Jira: `jira_url`, `jira_api_token`, `jira_project_key` required

3. **Encryption requirements**
   - All API tokens/keys stored in BYTEA/TEXT encrypted columns
   - Fernet symmetric encryption applied at application layer
   - Encryption key stored in Kubernetes Secret, never in database

## Troubleshooting

### Common Errors

**Error:** `PluginNotFoundError: Plugin 'zendesk' not registered`

**Solution:** Check registered plugins in PluginManager. Only 'servicedesk_plus' and 'jira' currently supported.

```python
from src.plugins.registry import PluginManager
manager = PluginManager()
available = manager.list_registered_plugins()
print([p['tool_type'] for p in available])
# Output: ['servicedesk_plus', 'jira']
```

**Error:** `ValidationError: Jira requires: jira_url, jira_api_token, jira_project_key`

**Solution:** Provide all required fields for Jira tenants:

```python
config = TenantConfigCreate(
    tenant_id="jira-tenant",
    name="Jira Tenant",
    tool_type="jira",
    jira_url="https://company.atlassian.net",  # Required
    jira_api_token="token",                     # Required
    jira_project_key="PROJ",                    # Required
    webhook_signing_secret="secret"
)
```

### Performance Optimization

**Index Usage Verification:**
```sql
EXPLAIN ANALYZE
SELECT * FROM tenant_configs WHERE tool_type = 'jira';

-- Expected plan:
-- Index Scan using idx_tenant_configs_tool_type
-- Execution time: <5ms for 1000 tenants
```

**JSONB Performance:**
```sql
-- Add GIN index for complex JSONB queries (optional)
CREATE INDEX idx_tenant_configs_preferences
ON tenant_configs USING gin (enhancement_preferences);
```

## Agent Orchestration Tables

The AI Agent system provides configurable AI agents with flexible triggers (webhooks, schedules) and tool integrations. Agents execute based on tenant-defined configurations and support multi-LLM provider routing via LiteLLM.

### Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────┐
│                         agents                           │
├──────────────────────────────────────────────────────────┤
│ PK  id                         UUID                      │
│ FK  tenant_id                  VARCHAR(100) → tenant_configs │
│ IDX name                       VARCHAR(255)              │
│ IDX status                     VARCHAR(20)               │
│     description                TEXT                      │
│     system_prompt              TEXT                      │
│     llm_config                 JSONB                     │
│     created_at                 TIMESTAMPTZ               │
│     updated_at                 TIMESTAMPTZ               │
│     created_by                 VARCHAR(255)              │
├──────────────────────────────────────────────────────────┤
│ Relationships:                                           │
│   → agent_triggers (1:N, CASCADE DELETE)                 │
│   → agent_tools (1:N, CASCADE DELETE)                    │
└──────────────────────────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────┐
│                    agent_triggers                        │
├──────────────────────────────────────────────────────────┤
│ PK  id                         UUID                      │
│ FK  agent_id                   UUID → agents (CASCADE)   │
│     trigger_type               VARCHAR(20)               │
│     webhook_url                VARCHAR(500)              │
│     hmac_secret                TEXT                      │
│     schedule_cron              VARCHAR(100)              │
│     payload_schema             JSONB                     │
│     created_at                 TIMESTAMPTZ               │
└──────────────────────────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────┐
│                     agent_tools                          │
├──────────────────────────────────────────────────────────┤
│ PK  (agent_id, tool_id)                                  │
│ FK  agent_id                   UUID → agents (CASCADE)   │
│     tool_id                    VARCHAR(100)              │
│     created_at                 TIMESTAMPTZ               │
└──────────────────────────────────────────────────────────┘
```

### Table: agents

Core agent configuration table storing LLM-powered agents with lifecycle management.

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| **id** | UUID | NOT NULL | uuid_generate_v4() | Primary key |
| **tenant_id** | VARCHAR(100) | NOT NULL | - | Foreign key to tenant_configs |
| **name** | VARCHAR(255) | NOT NULL | - | Human-readable agent name |
| **description** | TEXT | NULL | - | Optional detailed description |
| **status** | VARCHAR(20) | NOT NULL | - | Agent lifecycle status (draft, active, suspended, inactive) |
| **system_prompt** | TEXT | NOT NULL | - | LLM system prompt (10-32000 chars) |
| **llm_config** | JSONB | NOT NULL | '{}' | LLM configuration (provider, model, temperature, max_tokens) |
| **created_at** | TIMESTAMPTZ | NOT NULL | now() | Creation timestamp |
| **updated_at** | TIMESTAMPTZ | NOT NULL | now() | Last update timestamp |
| **created_by** | VARCHAR(255) | NULL | - | Creator identifier (email or user_id) |

#### Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| **agents_pkey** | id | PRIMARY KEY | Primary key uniqueness |
| **idx_agents_tenant_id_status** | tenant_id, status | BTREE | Fast tenant agent queries with status filtering |

#### Constraints

- **CHECK** `status IN ('draft', 'active', 'suspended', 'inactive')`
- **FOREIGN KEY** `tenant_id → tenant_configs(tenant_id)`

#### LLM Config JSONB Structure

```json
{
  "provider": "litellm",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 1.0,
  "frequency_penalty": 0.0
}
```

**Supported Models (2025):**
- OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- Anthropic: claude-3-5-sonnet, claude-3-opus, claude-3-sonnet, claude-3-haiku
- Open Source via LiteLLM: ollama/llama3, ollama/mistral

#### Agent Lifecycle Status

| Status | Description | Valid Transitions |
|--------|-------------|-------------------|
| **draft** | Agent created but not activated | → active |
| **active** | Agent running and processing triggers | → suspended, → inactive |
| **suspended** | Temporarily paused, triggers ignored | → active, → inactive |
| **inactive** | Soft deleted, triggers disabled | (terminal state) |

### Table: agent_triggers

Agent trigger configurations supporting webhook and scheduled execution.

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| **id** | UUID | NOT NULL | uuid_generate_v4() | Primary key |
| **agent_id** | UUID | NOT NULL | - | Foreign key to agents (CASCADE DELETE) |
| **trigger_type** | VARCHAR(20) | NOT NULL | - | Trigger type (webhook, schedule) |
| **webhook_url** | VARCHAR(500) | NULL | - | Webhook endpoint URL (for webhook triggers) |
| **hmac_secret** | TEXT | NULL | - | HMAC secret for webhook validation |
| **schedule_cron** | VARCHAR(100) | NULL | - | Cron expression (for schedule triggers) |
| **payload_schema** | JSONB | NULL | - | Optional JSON schema for webhook payload validation |
| **created_at** | TIMESTAMPTZ | NOT NULL | now() | Creation timestamp |

#### Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| **agent_triggers_pkey** | id | PRIMARY KEY | Primary key uniqueness |
| **idx_agent_triggers_agent_id** | agent_id | BTREE | Fast agent trigger lookups |
| **idx_agent_triggers_type** | trigger_type | BTREE | Fast webhook vs schedule filtering |

#### Constraints

- **CHECK** `trigger_type IN ('webhook', 'schedule')`
- **FOREIGN KEY** `agent_id → agents(id) ON DELETE CASCADE`

#### Trigger Types

**Webhook Trigger:**
```json
{
  "trigger_type": "webhook",
  "webhook_url": "/agents/550e8400-e29b-41d4-a716-446655440000/webhook",
  "hmac_secret": "encrypted_secret_here",
  "payload_schema": {
    "type": "object",
    "properties": {
      "ticket_id": {"type": "string"},
      "action": {"type": "string"}
    },
    "required": ["ticket_id"]
  }
}
```

**Schedule Trigger:**
```json
{
  "trigger_type": "schedule",
  "schedule_cron": "0 9 * * *"  // Daily at 9 AM
}
```

Common Cron Patterns:
- `0 * * * *` - Every hour
- `0 9 * * *` - Daily at 9 AM
- `0 9 * * 1` - Every Monday at 9 AM
- `*/15 * * * *` - Every 15 minutes

### Table: agent_tools

Many-to-many junction table mapping agents to available tools (ServiceDesk Plus, Jira, etc.).

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| **agent_id** | UUID | NOT NULL | - | Foreign key to agents (CASCADE DELETE) |
| **tool_id** | VARCHAR(100) | NOT NULL | - | Tool identifier (servicedesk_plus, jira, zendesk) |
| **created_at** | TIMESTAMPTZ | NOT NULL | now() | Creation timestamp |

#### Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| **agent_tools_pkey** | (agent_id, tool_id) | PRIMARY KEY | Composite primary key uniqueness |

#### Constraints

- **PRIMARY KEY** `(agent_id, tool_id)` (composite)
- **FOREIGN KEY** `agent_id → agents(id) ON DELETE CASCADE`

#### Tool IDs

Available tools (aligned with plugin registry):
- `servicedesk_plus` - ManageEngine ServiceDesk Plus
- `jira` - Atlassian Jira Service Management
- `zendesk` - Zendesk Support (future)

### Query Examples

**Get all active agents for tenant:**
```sql
SELECT id, name, status, llm_config->>'model' as model
FROM agents
WHERE tenant_id = 'acme-corp' AND status = 'active';
-- Uses idx_agents_tenant_id_status
```

**Get agent with triggers and tools:**
```sql
SELECT
  a.id, a.name, a.status,
  t.trigger_type, t.webhook_url, t.schedule_cron,
  array_agg(at.tool_id) as tools
FROM agents a
LEFT JOIN agent_triggers t ON a.id = t.agent_id
LEFT JOIN agent_tools at ON a.id = at.agent_id
WHERE a.id = '550e8400-e29b-41d4-a716-446655440000'
GROUP BY a.id, t.trigger_type, t.webhook_url, t.schedule_cron;
```

**Find agents using specific model:**
```sql
SELECT tenant_id, name, llm_config->>'model' as model
FROM agents
WHERE llm_config->>'model' = 'claude-3-5-sonnet';
```

**Get webhook triggers with URLs:**
```sql
SELECT a.name, t.webhook_url, t.created_at
FROM agent_triggers t
JOIN agents a ON t.agent_id = a.id
WHERE t.trigger_type = 'webhook'
ORDER BY t.created_at DESC;
-- Uses idx_agent_triggers_type
```

### Migration History

#### Migration facc8d95bcbd (2025-11-05)
**Story:** 8.2 - Agent Database Schema and Models

**Changes:**
- Created `agents` table with JSONB llm_config
- Created `agent_triggers` table with webhook/schedule support
- Created `agent_tools` junction table with composite PK
- Added indexes: `idx_agents_tenant_id_status`, `idx_agent_triggers_agent_id`, `idx_agent_triggers_type`
- Added CHECK constraints for status and trigger_type enums
- Configured CASCADE DELETE for child tables

**Purpose:** Enable AI agent orchestration with flexible trigger mechanisms and tool integrations

### Data Validation

#### Pydantic Schema Validation

**Agent Creation:**
```python
from src.schemas.agent import AgentCreate, LLMConfig, AgentTriggerCreate

agent = AgentCreate(
    name="Ticket Enhancement Agent",
    system_prompt="You are a helpful assistant for ticket enhancement...",
    llm_config=LLMConfig(model="gpt-4", temperature=0.7, max_tokens=4096),
    status="draft",
    triggers=[
        AgentTriggerCreate(
            trigger_type="webhook",
            webhook_url="/agents/uuid-123/webhook"
        )
    ],
    tool_ids=["servicedesk_plus"]
)
```

**Validation Rules:**
1. Active agents must have at least one trigger
2. System prompt length: 10-32000 characters
3. Temperature range: 0.0-2.0
4. Max tokens range: 1-32000
5. Status transitions: draft → active, active ↔ suspended, active/suspended → inactive
6. Schedule triggers require valid cron expression
7. Model must be in allowed list (validated against 2025 LiteLLM catalog)

## Future Extensions

### Planned Tool Additions

**Zendesk (Story 7.8):**
```sql
-- Future migration
ALTER TABLE tenant_configs
ADD COLUMN zendesk_subdomain VARCHAR(100),
ADD COLUMN zendesk_api_token_encrypted BYTEA;
```

**ServiceNow (Story 7.9):**
```sql
-- Future migration
ALTER TABLE tenant_configs
ADD COLUMN servicenow_instance_url VARCHAR(500),
ADD COLUMN servicenow_api_key_encrypted BYTEA;
```

### Multi-Tool Per Tenant (Future)

Support tenants using multiple tools simultaneously:
```sql
-- Potential future schema change
ALTER TABLE tenant_configs
ALTER COLUMN tool_type TYPE VARCHAR(50)[];
-- tool_type becomes array: ["jira", "servicedesk_plus"]
```

### Agent Enhancements (Future)

**Agent Execution History:**
```sql
-- Track agent invocations and results
CREATE TABLE agent_executions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  trigger_id UUID REFERENCES agent_triggers(id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status VARCHAR(20) NOT NULL,  -- running, completed, failed
  input_payload JSONB,
  output_result JSONB,
  error_message TEXT,
  token_usage JSONB
);
CREATE INDEX idx_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX idx_agent_executions_started_at ON agent_executions(started_at DESC);
```

**Agent Version Control:**
```sql
-- Track agent configuration changes
CREATE TABLE agent_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  system_prompt TEXT NOT NULL,
  llm_config JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by VARCHAR(255)
);
CREATE UNIQUE INDEX idx_agent_versions_agent_version ON agent_versions(agent_id, version_number);
```
