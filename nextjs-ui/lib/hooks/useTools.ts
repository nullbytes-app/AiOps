/**
 * React Query hooks for OpenAPI Tool Import
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ImportToolsRequest, ParseSpecRequest } from '../api/tools';
import * as toolsApi from '../api/tools';
import { toast } from 'sonner';

/**
 * Parse OpenAPI spec (client-side validation)
 * Does not persist, just validates and extracts operations
 */
export function useParseSpec() {
  return useMutation({
    mutationFn: (data: ParseSpecRequest) => toolsApi.parseSpec(data),
    onError: (error: Error) => {
      toast.error(`Invalid OpenAPI spec: ${error.message}`);
    },
  });
}

/**
 * Import tools from parsed spec
 */
export function useImportTools() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ImportToolsRequest) => toolsApi.importTools(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      toast.success(`${result.imported_count} tool(s) imported successfully`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to import tools: ${error.message}`);
    },
  });
}

/**
 * List all tools
 */
export function useTools() {
  return useQuery({
    queryKey: ['tools'],
    queryFn: toolsApi.listTools,
  });
}

/**
 * Get single tool by ID
 */
export function useTool(id: string) {
  return useQuery({
    queryKey: ['tools', id],
    queryFn: () => toolsApi.getTool(id),
    enabled: !!id,
  });
}

/**
 * Delete tool
 */
export function useDeleteTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => toolsApi.deleteTool(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      toast.success('Tool deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete tool: ${error.message}`);
    },
  });
}
