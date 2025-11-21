/**
 * useTestAgent Hook
 *
 * TanStack Query hook for testing agent execution.
 * Follows 2025 best practices with object-based config.
 */

import { useMutation } from '@tanstack/react-query';
import { testAgent, type AgentTestResponse } from '@/lib/api/agents';
import type { AgentTestInput } from '@/lib/validations/agents';

interface TestAgentMutationInput {
  agentId: string;
  data: AgentTestInput;
}

/**
 * Hook for executing agent tests
 *
 * @example
 * ```tsx
 * const testMutation = useTestAgent();
 *
 * await testMutation.mutateAsync({
 *   agentId: '123',
 *   data: { message: 'Test message' },
 * });
 * ```
 */
export function useTestAgent() {
  return useMutation<AgentTestResponse, Error, TestAgentMutationInput>({
    mutationFn: async ({ agentId, data }: TestAgentMutationInput) => {
      const response = await testAgent(agentId, data);
      return response;
    },
    // No cache invalidation needed - test execution doesn't modify data
    onError: (error) => {
      console.error('[useTestAgent] Test execution failed:', error);
    },
  });
}
