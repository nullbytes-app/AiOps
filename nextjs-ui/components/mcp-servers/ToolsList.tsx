/**
 * Tools List Component
 *
 * Displays list of tools discovered from an MCP server
 */

'use client';

import React from 'react';
import { Wrench, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface Tool {
  name: string;
  description?: string;
  input_schema?: Record<string, unknown>;
}

interface ToolsListProps {
  tools: Tool[];
}

export function ToolsList({ tools }: ToolsListProps) {
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());

  const toggleExpand = (index: number) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedTools(newExpanded);
  };

  if (tools.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <Wrench className="h-12 w-12 text-text-secondary mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-text-primary mb-2">No Tools Available</h3>
        <p className="text-text-secondary">
          This server has not exposed any tools. Test the connection to discover tools.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">
          Available Tools ({tools.length})
        </h3>
      </div>

      <div className="space-y-2">
        {tools.map((tool, index) => {
          const isExpanded = expandedTools.has(index);

          return (
            <div key={index} className="glass-card">
              <button
                onClick={() => toggleExpand(index)}
                className="w-full p-4 text-left hover:bg-white/30 transition-colors rounded-lg"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5 text-text-secondary" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-text-secondary" />
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
                      <Wrench className="h-5 w-5 text-accent-blue" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold text-text-primary">{tool.name}</h4>
                    {tool.description && (
                      <p className="text-sm text-text-secondary mt-1">{tool.description}</p>
                    )}
                  </div>
                </div>
              </button>

              {/* Expanded Schema View */}
              {isExpanded && tool.input_schema && (
                <div className="px-4 pb-4">
                  <div className="ml-14 p-3 bg-white/50 rounded-lg border border-border">
                    <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                      Input Schema
                    </h5>
                    <pre className="text-xs text-text-primary overflow-x-auto">
                      {JSON.stringify(tool.input_schema, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
