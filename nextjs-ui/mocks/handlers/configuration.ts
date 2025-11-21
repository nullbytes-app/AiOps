/**
 * MSW Configuration Handlers
 *
 * Mock API handlers for Configuration pages:
 * - Tenants CRUD (/api/v1/tenants)
 * - Agents CRUD (/api/v1/agents)
 * - LLM Providers CRUD (/api/v1/llm-providers)
 * - MCP Servers CRUD (/api/v1/mcp-servers)
 */

import { http, HttpResponse } from 'msw'

/**
 * Mock Tenants Data
 */
let mockTenants = [
  {
    id: '1',
    name: 'Acme Corp',
    description: 'Main production tenant',
    logo_url: 'https://placehold.co/100x100/4f46e5/ffffff?text=AC',
    agent_count: 5,
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-15T14:30:00Z',
  },
  {
    id: '2',
    name: 'TechStart Inc',
    description: 'Startup tenant for innovation projects',
    logo_url: 'https://placehold.co/100x100/06b6d4/ffffff?text=TS',
    agent_count: 3,
    created_at: '2025-01-10T08:00:00Z',
    updated_at: '2025-01-16T09:15:00Z',
  },
  {
    id: '3',
    name: 'Enterprise Solutions',
    description: 'Large enterprise customer',
    logo_url: '',
    agent_count: 12,
    created_at: '2024-12-15T12:00:00Z',
    updated_at: '2025-01-17T16:45:00Z',
  },
]

/**
 * Mock Agents Data
 */
let mockAgents = [
  {
    id: '1',
    name: 'Ticket Enhancer',
    type: 'Webhook-Triggered',
    status: 'active',
    system_prompt:
      'You are a helpful assistant that enhances support tickets with additional context and categorization.',
    llm_model: 'gpt-4o-mini',
    llm_provider_id: '1',
    temperature: 0.7,
    max_tokens: 2000,
    tools_count: 5,
    tool_ids: ['1', '2', '5'],
    last_run: '2025-01-18T10:30:00Z',
    created_at: '2025-01-05T09:00:00Z',
    updated_at: '2025-01-18T10:30:00Z',
  },
  {
    id: '2',
    name: 'Context Gatherer',
    type: 'Task-Based',
    status: 'inactive',
    system_prompt:
      'Gather additional context from external sources to enrich ticket information.',
    llm_model: 'claude-3-5-sonnet-20241022',
    llm_provider_id: '2',
    temperature: 0.5,
    max_tokens: 4000,
    tools_count: 3,
    tool_ids: ['3', '4'],
    last_run: '2025-01-17T15:20:00Z',
    created_at: '2025-01-08T11:00:00Z',
    updated_at: '2025-01-17T15:20:00Z',
  },
  {
    id: '3',
    name: 'Customer Insights Agent',
    type: 'Conversational',
    status: 'active',
    system_prompt: 'Analyze customer sentiment and provide insights.',
    llm_model: 'gpt-4-turbo',
    llm_provider_id: '1',
    temperature: 0.8,
    max_tokens: 3000,
    tools_count: 7,
    tool_ids: ['1', '2', '3', '6', '7'],
    last_run: '2025-01-18T14:00:00Z',
    created_at: '2025-01-12T13:00:00Z',
    updated_at: '2025-01-18T14:00:00Z',
  },
]

/**
 * Mock LLM Providers Data
 */
let mockLLMProviders = [
  {
    id: '1',
    name: 'OpenAI Production',
    type: 'openai',
    base_url: '',
    api_key_set: true,
    model_count: 15,
    status: 'healthy',
    last_health_check: '2025-01-18T14:30:00Z',
    created_at: '2024-12-01T10:00:00Z',
    updated_at: '2025-01-18T14:30:00Z',
  },
  {
    id: '2',
    name: 'Anthropic',
    type: 'anthropic',
    base_url: '',
    api_key_set: true,
    model_count: 8,
    status: 'healthy',
    last_health_check: '2025-01-18T14:28:00Z',
    created_at: '2024-12-05T11:00:00Z',
    updated_at: '2025-01-18T14:28:00Z',
  },
  {
    id: '3',
    name: 'Azure OpenAI',
    type: 'azure_openai',
    base_url: 'https://my-instance.openai.azure.com',
    api_key_set: true,
    model_count: 10,
    status: 'healthy',
    last_health_check: '2025-01-18T14:25:00Z',
    created_at: '2025-01-03T09:00:00Z',
    updated_at: '2025-01-18T14:25:00Z',
  },
  {
    id: '4',
    name: 'Custom LiteLLM',
    type: 'custom_litellm',
    base_url: 'https://litellm.example.com/v1',
    api_key_set: false,
    model_count: 0,
    status: 'unknown',
    last_health_check: null,
    created_at: '2025-01-15T14:00:00Z',
    updated_at: '2025-01-15T14:00:00Z',
  },
]

/**
 * Mock Models Data
 */
const mockModels: Record<string, any[]> = {
  '1': [
    {
      id: 'gpt-4o-mini',
      context_window: 128000,
      input_cost_per_1k: 0.00015,
      output_cost_per_1k: 0.0006,
    },
    {
      id: 'gpt-4-turbo',
      context_window: 128000,
      input_cost_per_1k: 0.01,
      output_cost_per_1k: 0.03,
    },
    {
      id: 'gpt-4',
      context_window: 8192,
      input_cost_per_1k: 0.03,
      output_cost_per_1k: 0.06,
    },
    {
      id: 'gpt-3.5-turbo',
      context_window: 16385,
      input_cost_per_1k: 0.0005,
      output_cost_per_1k: 0.0015,
    },
  ],
  '2': [
    {
      id: 'claude-3-5-sonnet-20241022',
      context_window: 200000,
      input_cost_per_1k: 0.003,
      output_cost_per_1k: 0.015,
    },
    {
      id: 'claude-3-opus-20240229',
      context_window: 200000,
      input_cost_per_1k: 0.015,
      output_cost_per_1k: 0.075,
    },
    {
      id: 'claude-3-haiku-20240307',
      context_window: 200000,
      input_cost_per_1k: 0.00025,
      output_cost_per_1k: 0.00125,
    },
  ],
  '3': [
    {
      id: 'gpt-4-azure',
      context_window: 128000,
      input_cost_per_1k: 0.01,
      output_cost_per_1k: 0.03,
    },
    {
      id: 'gpt-35-turbo-azure',
      context_window: 16385,
      input_cost_per_1k: 0.0005,
      output_cost_per_1k: 0.0015,
    },
  ],
}

/**
 * Mock MCP Servers Data
 */
let mockMCPServers = [
  {
    id: '1',
    name: 'Filesystem Server',
    type: 'stdio',
    status: 'healthy',
    url: null,
    command: '/usr/local/bin/mcp-fs-server',
    env_vars: {
      ALLOWED_PATHS: '/home/user/projects',
      MAX_FILE_SIZE: '10485760',
    },
    tools_count: 8,
    health_check_interval: 60,
    last_health_check: '2025-01-18T14:30:00Z',
    created_at: '2024-12-10T10:00:00Z',
    updated_at: '2025-01-18T14:30:00Z',
  },
  {
    id: '2',
    name: 'GitHub MCP',
    type: 'HTTP',
    status: 'healthy',
    url: 'https://mcp.github.com',
    command: null,
    env_vars: {},
    tools_count: 12,
    health_check_interval: 60,
    last_health_check: '2025-01-18T14:28:00Z',
    created_at: '2024-12-15T11:00:00Z',
    updated_at: '2025-01-18T14:28:00Z',
  },
  {
    id: '3',
    name: 'Slack SSE Server',
    type: 'SSE',
    status: 'healthy',
    url: 'https://slack-mcp.example.com/events',
    command: null,
    env_vars: {},
    tools_count: 5,
    health_check_interval: 30,
    last_health_check: '2025-01-18T14:29:00Z',
    created_at: '2025-01-05T09:00:00Z',
    updated_at: '2025-01-18T14:29:00Z',
  },
]

/**
 * Mock Tools Data
 */
let mockTools = [
  {
    id: '1',
    name: 'search_knowledge_base',
    description: 'Search the knowledge base for relevant articles',
    source: 'openapi',
    parameters: ['query', 'limit'],
  },
  {
    id: '2',
    name: 'create_jira_ticket',
    description: 'Create a new JIRA ticket',
    source: 'openapi',
    parameters: ['title', 'description', 'priority'],
  },
  {
    id: '3',
    name: 'read_file',
    description: 'Read file contents from filesystem',
    source: 'mcp',
    mcp_server_id: '1',
    parameters: ['path'],
  },
  {
    id: '4',
    name: 'write_file',
    description: 'Write content to a file',
    source: 'mcp',
    mcp_server_id: '1',
    parameters: ['path', 'content'],
  },
  {
    id: '5',
    name: 'get_github_pr',
    description: 'Get GitHub pull request details',
    source: 'mcp',
    mcp_server_id: '2',
    parameters: ['owner', 'repo', 'pr_number'],
  },
  {
    id: '6',
    name: 'send_slack_message',
    description: 'Send a message to Slack channel',
    source: 'mcp',
    mcp_server_id: '3',
    parameters: ['channel', 'message'],
  },
  {
    id: '7',
    name: 'analyze_sentiment',
    description: 'Analyze text sentiment',
    source: 'openapi',
    parameters: ['text'],
  },
]

/**
 * ============================================
 * TENANTS HANDLERS
 * ============================================
 */

export const tenantsHandlers = [
  // GET /api/v1/tenants - List all tenants
  http.get('/api/v1/tenants', ({ request }) => {
    const url = new URL(request.url)
    const search = url.searchParams.get('search')
    const sortBy = url.searchParams.get('sortBy') || 'created_at'
    const sortOrder = url.searchParams.get('sortOrder') || 'desc'
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '20')

    let filtered = [...mockTenants]

    // Apply search filter
    if (search) {
      filtered = filtered.filter((t) =>
        t.name.toLowerCase().includes(search.toLowerCase())
      )
    }

    // Apply sorting
    filtered.sort((a: any, b: any) => {
      const aVal = a[sortBy]
      const bVal = b[sortBy]
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1
      }
      return aVal < bVal ? 1 : -1
    })

    // Apply pagination
    const start = (page - 1) * limit
    const end = start + limit
    const paginatedData = filtered.slice(start, end)

    return HttpResponse.json({
      data: paginatedData,
      total: filtered.length,
      page,
      limit,
    })
  }),

  // GET /api/v1/tenants/:id - Get tenant by ID
  http.get('/api/v1/tenants/:id', ({ params }) => {
    const tenant = mockTenants.find((t) => t.id === params.id)

    if (!tenant) {
      return HttpResponse.json({ error: 'Tenant not found' }, { status: 404 })
    }

    return HttpResponse.json(tenant)
  }),

  // POST /api/v1/tenants - Create new tenant
  http.post('/api/v1/tenants', async ({ request }) => {
    const body = (await request.json()) as any

    const newTenant = {
      id: `${Date.now()}`,
      ...body,
      agent_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockTenants.push(newTenant)

    return HttpResponse.json(newTenant, { status: 201 })
  }),

  // PUT /api/v1/tenants/:id - Update tenant
  http.put('/api/v1/tenants/:id', async ({ params, request }) => {
    const body = (await request.json()) as any
    const index = mockTenants.findIndex((t) => t.id === params.id)

    if (index === -1) {
      return HttpResponse.json({ error: 'Tenant not found' }, { status: 404 })
    }

    mockTenants[index] = {
      ...mockTenants[index],
      ...body,
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(mockTenants[index])
  }),

  // DELETE /api/v1/tenants/:id - Delete tenant
  http.delete('/api/v1/tenants/:id', ({ params }) => {
    const index = mockTenants.findIndex((t) => t.id === params.id)

    if (index === -1) {
      return HttpResponse.json({ error: 'Tenant not found' }, { status: 404 })
    }

    mockTenants = mockTenants.filter((t) => t.id !== params.id)

    return new HttpResponse(null, { status: 204 })
  }),
]

/**
 * ============================================
 * AGENTS HANDLERS
 * ============================================
 */

export const agentsHandlers = [
  // GET /api/v1/agents - List all agents
  http.get('/api/v1/agents', ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    const search = url.searchParams.get('search')

    let filtered = [...mockAgents]

    // Apply status filter
    if (status && status !== 'all') {
      filtered = filtered.filter((a) => a.status === status)
    }

    // Apply search filter
    if (search) {
      filtered = filtered.filter((a) =>
        a.name.toLowerCase().includes(search.toLowerCase())
      )
    }

    return HttpResponse.json({
      data: filtered,
      total: filtered.length,
    })
  }),

  // GET /api/v1/agents/:id - Get agent by ID
  http.get('/api/v1/agents/:id', ({ params }) => {
    const agent = mockAgents.find((a) => a.id === params.id)

    if (!agent) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 })
    }

    return HttpResponse.json(agent)
  }),

  // POST /api/v1/agents - Create new agent
  http.post('/api/v1/agents', async ({ request }) => {
    const body = (await request.json()) as any

    const newAgent = {
      id: `${Date.now()}`,
      ...body,
      tools_count: body.tool_ids?.length || 0,
      last_run: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockAgents.push(newAgent)

    return HttpResponse.json(newAgent, { status: 201 })
  }),

  // PUT /api/v1/agents/:id - Update agent
  http.put('/api/v1/agents/:id', async ({ params, request }) => {
    const body = (await request.json()) as any
    const index = mockAgents.findIndex((a) => a.id === params.id)

    if (index === -1) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 })
    }

    mockAgents[index] = {
      ...mockAgents[index],
      ...body,
      tools_count: body.tool_ids?.length || mockAgents[index].tools_count,
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(mockAgents[index])
  }),

  // DELETE /api/v1/agents/:id - Delete agent
  http.delete('/api/v1/agents/:id', ({ params }) => {
    const index = mockAgents.findIndex((a) => a.id === params.id)

    if (index === -1) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 })
    }

    mockAgents = mockAgents.filter((a) => a.id !== params.id)

    return new HttpResponse(null, { status: 204 })
  }),

  // PUT /api/v1/agents/:id/tools - Update agent tools
  http.put('/api/v1/agents/:id/tools', async ({ params, request }) => {
    const body = (await request.json()) as { tool_ids: string[] }
    const index = mockAgents.findIndex((a) => a.id === params.id)

    if (index === -1) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 })
    }

    mockAgents[index] = {
      ...mockAgents[index],
      tool_ids: body.tool_ids,
      tools_count: body.tool_ids.length,
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(mockAgents[index])
  }),

  // POST /api/v1/agents/:id/test - Test agent execution
  http.post('/api/v1/agents/:id/test', async ({ params, request }) => {
    const body = (await request.json()) as { message: string }
    const agent = mockAgents.find((a) => a.id === params.id)

    if (!agent) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 })
    }

    // Simulate processing delay
    await new Promise((resolve) => setTimeout(resolve, 1500))

    return HttpResponse.json({
      response: {
        content: `Mock response from ${agent.name}: I received your message "${body.message}" and processed it successfully.`,
        tool_calls: [
          {
            name: 'search_knowledge_base',
            arguments: { query: body.message, limit: 5 },
            result: 'Found 3 relevant articles',
          },
        ],
      },
      metadata: {
        agent_id: agent.id,
        agent_name: agent.name,
        model: agent.llm_model,
        tokens_used: 245,
        duration_ms: 1432,
        cost: 0.0012,
        status: 'success',
        timestamp: new Date().toISOString(),
      },
    })
  }),
]

/**
 * ============================================
 * LLM PROVIDERS HANDLERS
 * ============================================
 */

export const llmProvidersHandlers = [
  // GET /api/v1/llm-providers - List all providers
  http.get('/api/v1/llm-providers', ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')

    let filtered = [...mockLLMProviders]

    // Apply status filter
    if (status && status !== 'all') {
      filtered = filtered.filter((p) => p.status === status)
    }

    return HttpResponse.json({
      data: filtered,
      total: filtered.length,
    })
  }),

  // GET /api/v1/llm-providers/:id - Get provider by ID
  http.get('/api/v1/llm-providers/:id', ({ params }) => {
    const provider = mockLLMProviders.find((p) => p.id === params.id)

    if (!provider) {
      return HttpResponse.json(
        { error: 'Provider not found' },
        { status: 404 }
      )
    }

    return HttpResponse.json(provider)
  }),

  // POST /api/v1/llm-providers - Create new provider
  http.post('/api/v1/llm-providers', async ({ request }) => {
    const body = (await request.json()) as any

    const newProvider = {
      id: `${Date.now()}`,
      ...body,
      api_key_set: !!body.api_key,
      model_count: 0,
      status: 'unknown',
      last_health_check: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    // Remove api_key from response (only store the fact it's set)
    const { api_key, ...responseData } = newProvider

    mockLLMProviders.push(responseData)

    return HttpResponse.json(responseData, { status: 201 })
  }),

  // PUT /api/v1/llm-providers/:id - Update provider
  http.put('/api/v1/llm-providers/:id', async ({ params, request }) => {
    const body = (await request.json()) as any
    const index = mockLLMProviders.findIndex((p) => p.id === params.id)

    if (index === -1) {
      return HttpResponse.json(
        { error: 'Provider not found' },
        { status: 404 }
      )
    }

    mockLLMProviders[index] = {
      ...mockLLMProviders[index],
      ...body,
      api_key_set: body.api_key ? true : mockLLMProviders[index].api_key_set,
      updated_at: new Date().toISOString(),
    }

    // Remove api_key from response
    const { api_key, ...responseData } = mockLLMProviders[index] as any

    return HttpResponse.json(responseData)
  }),

  // DELETE /api/v1/llm-providers/:id - Delete provider
  http.delete('/api/v1/llm-providers/:id', ({ params }) => {
    const index = mockLLMProviders.findIndex((p) => p.id === params.id)

    if (index === -1) {
      return HttpResponse.json(
        { error: 'Provider not found' },
        { status: 404 }
      )
    }

    mockLLMProviders = mockLLMProviders.filter((p) => p.id !== params.id)

    return new HttpResponse(null, { status: 204 })
  }),

  // POST /api/v1/llm-providers/test - Test provider connection
  http.post('/api/v1/llm-providers/test', async ({ request }) => {
    const body = (await request.json()) as any

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 800))

    // Simulate failure for specific test case
    if (body.api_key === 'invalid-key') {
      return HttpResponse.json(
        {
          success: false,
          error: 'Invalid API key. Please check your credentials.',
        },
        { status: 401 }
      )
    }

    // Get models based on provider type
    const modelsMap: Record<string, string[]> = {
      openai: [
        'gpt-4o-mini',
        'gpt-4-turbo',
        'gpt-4',
        'gpt-3.5-turbo',
        'text-embedding-ada-002',
      ],
      anthropic: [
        'claude-3-5-sonnet-20241022',
        'claude-3-opus-20240229',
        'claude-3-haiku-20240307',
      ],
      azure_openai: ['gpt-4-azure', 'gpt-35-turbo-azure'],
      custom_litellm: ['mock-model-1', 'mock-model-2'],
    }

    const models = modelsMap[body.type] || []

    return HttpResponse.json({
      success: true,
      response_time_ms: 245,
      models_found: models.length,
      models: models.map((id) => ({ id, name: id })),
    })
  }),

  // GET /api/v1/llm-providers/:id/models - Get provider models
  http.get('/api/v1/llm-providers/:id/models', ({ params }) => {
    const provider = mockLLMProviders.find((p) => p.id === params.id)

    if (!provider) {
      return HttpResponse.json(
        { error: 'Provider not found' },
        { status: 404 }
      )
    }

    const models = mockModels[params.id as string] || []

    return HttpResponse.json({
      models,
      total: models.length,
    })
  }),

  // POST /api/v1/llm-providers/:id/models/refresh - Refresh provider models
  http.post('/api/v1/llm-providers/:id/models/refresh', async ({ params }) => {
    const provider = mockLLMProviders.find((p) => p.id === params.id)

    if (!provider) {
      return HttpResponse.json(
        { error: 'Provider not found' },
        { status: 404 }
      )
    }

    // Simulate refresh delay
    await new Promise((resolve) => setTimeout(resolve, 1000))

    const models = mockModels[params.id as string] || []

    return HttpResponse.json({
      success: true,
      models_found: models.length,
      models,
    })
  }),
]

/**
 * ============================================
 * MCP SERVERS HANDLERS
 * ============================================
 */

export const mcpServersHandlers = [
  // GET /api/v1/mcp-servers - List all MCP servers
  http.get('/api/v1/mcp-servers', ({ request }) => {
    const url = new URL(request.url)
    const type = url.searchParams.get('type')
    const status = url.searchParams.get('status')
    const search = url.searchParams.get('search')

    let filtered = [...mockMCPServers]

    // Apply type filter
    if (type && type !== 'all') {
      filtered = filtered.filter((s) => s.type === type)
    }

    // Apply status filter
    if (status && status !== 'all') {
      filtered = filtered.filter((s) => s.status === status)
    }

    // Apply search filter
    if (search) {
      filtered = filtered.filter((s) =>
        s.name.toLowerCase().includes(search.toLowerCase())
      )
    }

    return HttpResponse.json({
      data: filtered,
      total: filtered.length,
    })
  }),

  // GET /api/v1/mcp-servers/:id - Get MCP server by ID
  http.get('/api/v1/mcp-servers/:id', ({ params }) => {
    const server = mockMCPServers.find((s) => s.id === params.id)

    if (!server) {
      return HttpResponse.json(
        { error: 'MCP server not found' },
        { status: 404 }
      )
    }

    return HttpResponse.json(server)
  }),

  // POST /api/v1/mcp-servers - Create new MCP server
  http.post('/api/v1/mcp-servers', async ({ request }) => {
    const body = (await request.json()) as any

    const newServer = {
      id: `${Date.now()}`,
      ...body,
      tools_count: 0,
      status: 'unknown',
      last_health_check: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    mockMCPServers.push(newServer)

    return HttpResponse.json(newServer, { status: 201 })
  }),

  // PUT /api/v1/mcp-servers/:id - Update MCP server
  http.put('/api/v1/mcp-servers/:id', async ({ params, request }) => {
    const body = (await request.json()) as any
    const index = mockMCPServers.findIndex((s) => s.id === params.id)

    if (index === -1) {
      return HttpResponse.json(
        { error: 'MCP server not found' },
        { status: 404 }
      )
    }

    mockMCPServers[index] = {
      ...mockMCPServers[index],
      ...body,
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(mockMCPServers[index])
  }),

  // DELETE /api/v1/mcp-servers/:id - Delete MCP server
  http.delete('/api/v1/mcp-servers/:id', ({ params }) => {
    const index = mockMCPServers.findIndex((s) => s.id === params.id)

    if (index === -1) {
      return HttpResponse.json(
        { error: 'MCP server not found' },
        { status: 404 }
      )
    }

    mockMCPServers = mockMCPServers.filter((s) => s.id !== params.id)

    return new HttpResponse(null, { status: 204 })
  }),

  // POST /api/v1/mcp-servers/test - Test MCP server connection
  http.post('/api/v1/mcp-servers/test', async ({ request }) => {
    const body = (await request.json()) as any

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 1200))

    // Simulate failure for specific test case
    if (body.url === 'https://fail.example.com') {
      return HttpResponse.json(
        {
          success: false,
          error: 'Connection timeout. Please check the URL and try again.',
        },
        { status: 504 }
      )
    }

    // Mock tools discovered based on server type
    const toolsMap: Record<string, any[]> = {
      stdio: [
        { name: 'read_file', description: 'Read file contents' },
        { name: 'write_file', description: 'Write to file' },
        { name: 'list_directory', description: 'List directory contents' },
        { name: 'delete_file', description: 'Delete a file' },
      ],
      HTTP: [
        { name: 'get_github_pr', description: 'Get pull request details' },
        { name: 'create_github_issue', description: 'Create GitHub issue' },
        { name: 'list_repositories', description: 'List repositories' },
      ],
      SSE: [
        { name: 'send_message', description: 'Send Slack message' },
        { name: 'list_channels', description: 'List Slack channels' },
        { name: 'get_user_info', description: 'Get user information' },
      ],
    }

    const tools = toolsMap[body.type] || []

    return HttpResponse.json({
      success: true,
      response_time_ms: 342,
      tools_found: tools.length,
      tools,
    })
  }),

  // GET /api/v1/mcp-servers/:id/tools - Get tools from MCP server
  http.get('/api/v1/mcp-servers/:id/tools', ({ params }) => {
    const server = mockMCPServers.find((s) => s.id === params.id)

    if (!server) {
      return HttpResponse.json(
        { error: 'MCP server not found' },
        { status: 404 }
      )
    }

    const serverTools = mockTools.filter((t) => t.mcp_server_id === params.id)

    return HttpResponse.json({
      tools: serverTools,
      total: serverTools.length,
    })
  }),

  // GET /api/v1/mcp-servers/:id/health - Get health check logs
  http.get('/api/v1/mcp-servers/:id/health', ({ params }) => {
    const server = mockMCPServers.find((s) => s.id === params.id)

    if (!server) {
      return HttpResponse.json(
        { error: 'MCP server not found' },
        { status: 404 }
      )
    }

    // Generate mock health logs (last 50 checks)
    const logs = Array.from({ length: 50 }, (_, i) => ({
      id: `log-${i}`,
      timestamp: new Date(
        Date.now() - i * server.health_check_interval * 1000
      ).toISOString(),
      status: i % 10 === 0 ? 'unhealthy' : 'healthy',
      response_time_ms: Math.floor(Math.random() * 500) + 100,
      error: i % 10 === 0 ? 'Connection timeout' : null,
    }))

    return HttpResponse.json({
      logs,
      total: logs.length,
    })
  }),
]

/**
 * ============================================
 * TOOLS HANDLERS
 * ============================================
 */

export const toolsHandlers = [
  // GET /api/v1/tools - List all tools
  http.get('/api/v1/tools', ({ request }) => {
    const url = new URL(request.url)
    const source = url.searchParams.get('source')

    let filtered = [...mockTools]

    // Apply source filter
    if (source && source !== 'all') {
      filtered = filtered.filter((t) => t.source === source)
    }

    return HttpResponse.json({
      data: filtered,
      total: filtered.length,
    })
  }),
]

/**
 * Export all configuration handlers
 */
export const configurationHandlers = [
  ...tenantsHandlers,
  ...agentsHandlers,
  ...llmProvidersHandlers,
  ...mcpServersHandlers,
  ...toolsHandlers,
]
