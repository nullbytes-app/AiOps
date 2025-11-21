/**
 * TypeScript types for LLM Cost API responses
 * Generated from src/schemas/llm_cost.py Pydantic models
 */

/**
 * Tenant spend summary DTO
 * Maps to Python TenantSpendDTO (lines 20-33)
 */
export interface TenantSpendDTO {
  tenant_id: string; // VARCHAR(100) matching tenant_configs.tenant_id
  tenant_name: string;
  total_spend: number; // USD amount (>= 0.0)
  rank: number; // Rank by spend (1=highest, range: 1-10)
}

/**
 * Agent spend summary DTO with execution statistics
 * Maps to Python AgentSpendDTO (lines 35-56)
 */
export interface AgentSpendDTO {
  agent_id: string | null; // UUID or null
  agent_name: string;
  execution_count: number; // Number of executions (>= 0)
  total_cost: number; // Total cost in USD (>= 0.0)
  avg_cost: number; // Average cost per execution in USD (>= 0.0)
}

/**
 * Overall cost summary with multiple time periods
 * Maps to Python CostSummaryDTO (lines 187-201)
 *
 * Used for API endpoint: GET /api/v1/costs/summary
 */
export interface CostSummaryDTO {
  today_spend: number; // Spend today in USD (>= 0.0)
  week_spend: number; // Spend this week (7-day rolling) in USD (>= 0.0)
  month_spend: number; // Spend this month (MTD) in USD (>= 0.0)
  total_spend_30d: number; // Total spend last 30 days in USD (>= 0.0)
  top_tenant: TenantSpendDTO | null; // Top spending tenant (may be null if no data)
  top_agent: AgentSpendDTO | null; // Top spending agent (may be null if no data)
}

/**
 * API response wrapper for cost summary
 * Includes optional metadata like request timestamp
 */
export interface CostSummaryResponse {
  data: CostSummaryDTO;
  timestamp?: string; // ISO 8601 format
}

/**
 * Daily spend data point from backend API
 * Maps to Python schema: src/schemas/llm_cost.py:75-89 (DailySpendDTO)
 * Used for API endpoint: GET /api/v1/costs/trend?days=30
 */
export interface DailySpendDTO {
  /** Date in YYYY-MM-DD format (e.g., "2025-01-15") */
  date: string;
  /** Total spend for the day in USD */
  total_spend: number;
  /** Number of LLM API calls on this day */
  transaction_count: number;
}

/**
 * Token breakdown data point from backend API
 * Maps to Python schema: src/schemas/llm_cost.py (TokenBreakdownDTO)
 * Used for API endpoint: GET /api/v1/costs/token-breakdown?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
 */
export interface TokenBreakdownDTO {
  /** Token type: 'input' | 'output' */
  tokenType: 'input' | 'output';
  /** Total tokens of this type */
  count: number;
  /** USD cost for this token type */
  cost: number;
}

/**
 * Token breakdown with calculated percentage (client-side)
 * Extends TokenBreakdownDTO with percentage field
 */
export interface TokenBreakdownWithPercentage extends TokenBreakdownDTO {
  /** Percentage of total tokens: (count / total) * 100 */
  percentage: number;
}

/**
 * Budget-related Types
 * =====================
 * Types for budget utilization and tenant cost management
 */

/**
 * Agent spend data within a tenant (budget context)
 * Used for agent-level breakdown in budget utilization views
 */
export interface BudgetAgentSpendDTO {
  /** Unique agent identifier */
  agent_id: string;

  /** Human-readable agent name */
  agent_name: string;

  /** Amount spent by this agent in USD */
  spent_amount: number;

  /** Percentage of tenant's total spend (0-100) */
  percentage_of_tenant: number;
}

/**
 * Budget utilization data for a single tenant
 * Maps to Python BudgetUtilizationDTO (backend schema to be implemented)
 */
export interface BudgetUtilizationDTO {
  /** Unique tenant identifier */
  tenant_id: string;

  /** Human-readable tenant name */
  tenant_name: string;

  /** Budget allocation in USD, null if not configured */
  budget_amount: number | null;

  /** Cumulative amount spent in USD */
  spent_amount: number;

  /** Utilization percentage (0-100+), calculated as (spent/budget) * 100 */
  utilization_percentage: number;

  /** Breakdown of spend by agent */
  agent_breakdown: BudgetAgentSpendDTO[];

  /** ISO 8601 timestamp of last data update */
  last_updated: string;
}

/**
 * API response for budget utilization endpoint
 * Used for GET /api/v1/costs/budget-utilization
 */
export interface BudgetUtilizationResponse {
  /** Array of tenant budget data */
  data: BudgetUtilizationDTO[];

  /** Total number of tenants (for pagination) */
  total_count: number;

  /** Current page number (1-indexed) */
  page: number;

  /** Number of items per page */
  page_size: number;
}

/**
 * Filter options for budget utilization queries
 */
export type BudgetFilter = "all" | "over_budget" | "high_utilization";

/**
 * Sort options for budget utilization list
 */
export type BudgetSortBy = "utilization" | "name" | "budget";
