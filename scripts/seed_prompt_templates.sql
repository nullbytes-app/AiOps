-- Seed built-in prompt templates
-- Run this script to populate the agent_prompt_templates table with default templates

-- Get the default tenant ID
DO $$
DECLARE
    default_tenant_id VARCHAR;
BEGIN
    -- Get the first active tenant
    SELECT tenant_id INTO default_tenant_id
    FROM tenant_configs
    WHERE is_active = true
    LIMIT 1;

    -- Insert built-in templates
    INSERT INTO agent_prompt_templates (
        id,
        tenant_id,
        name,
        description,
        template_text,
        is_builtin,
        is_active
    ) VALUES
    (
        gen_random_uuid(),
        default_tenant_id,
        'Ticket Enhancement',
        'AI assistant specialized in enhancing support tickets',
        'You are a helpful AI assistant specialized in enhancing support tickets.
Your role is to:
1. Analyze ticket content and context
2. Suggest improvements and additions
3. Identify relevant knowledge base articles
4. Recommend similar tickets for reference

Always maintain a professional tone and focus on clarity and completeness.',
        true,
        true
    ),
    (
        gen_random_uuid(),
        default_tenant_id,
        'RCA Analysis',
        'Expert in Root Cause Analysis (RCA)',
        'You are an expert in Root Cause Analysis (RCA).
Your role is to:
1. Analyze incident reports and logs
2. Identify root causes systematically
3. Suggest preventive measures
4. Create actionable remediation steps

Follow the 5 Whys methodology in your analysis.',
        true,
        true
    ),
    (
        gen_random_uuid(),
        default_tenant_id,
        'General Purpose',
        'General-purpose AI assistant',
        'You are a helpful AI assistant.
Your role is to:
1. Understand user requests
2. Provide accurate and helpful responses
3. Ask clarifying questions when needed
4. Maintain context across conversations

Be concise, professional, and solution-focused.',
        true,
        true
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Built-in templates seeded successfully for tenant: %', default_tenant_id;
END $$;
