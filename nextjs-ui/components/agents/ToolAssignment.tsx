"use client";

import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button, Input } from '@/components/ui';
import { GripVertical, X, Plus, Search } from 'lucide-react';

/**
 * Tool Assignment Component
 *
 * Drag-and-drop interface for assigning tools to agents
 * Uses dnd-kit for accessibility and keyboard navigation
 *
 * @example
 * ```tsx
 * <ToolAssignment
 *   availableTools={allTools}
 *   assignedToolIds={agent.tool_ids}
 *   onAssign={handleAssignTools}
 *   isLoading={isAssigning}
 * />
 * ```
 */

interface Tool {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

interface ToolAssignmentProps {
  availableTools: Tool[];
  assignedToolIds: string[];
  onAssign: (toolIds: string[]) => void;
  isLoading?: boolean;
}

interface SortableToolItemProps {
  tool: Tool;
  onRemove: () => void;
}

function SortableToolItem({ tool, onRemove }: SortableToolItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: tool.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="glass-card p-3 flex items-center gap-3 group"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-text-secondary hover:text-text-primary"
        aria-label={`Drag ${tool.name}`}
      >
        <GripVertical className="w-5 h-5" />
      </button>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-text-primary">{tool.name}</div>
        {tool.description && (
          <div className="text-xs text-text-secondary truncate">
            {tool.description}
          </div>
        )}
      </div>
      {tool.category && (
        <span className="px-2 py-1 rounded-md bg-accent-blue/20 text-accent-blue text-xs font-medium">
          {tool.category}
        </span>
      )}
      <button
        onClick={onRemove}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-600"
        aria-label={`Remove ${tool.name}`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

interface AvailableToolItemProps {
  tool: Tool;
  onAdd: () => void;
}

function AvailableToolItem({ tool, onAdd }: AvailableToolItemProps) {
  return (
    <div className="glass-card p-3 flex items-center gap-3 group hover:bg-white/30 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="font-medium text-text-primary">{tool.name}</div>
        {tool.description && (
          <div className="text-xs text-text-secondary truncate">
            {tool.description}
          </div>
        )}
      </div>
      {tool.category && (
        <span className="px-2 py-1 rounded-md bg-accent-blue/20 text-accent-blue text-xs font-medium">
          {tool.category}
        </span>
      )}
      <button
        onClick={onAdd}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-accent-blue hover:text-accent-blue/80"
        aria-label={`Add ${tool.name}`}
      >
        <Plus className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToolAssignment({
  availableTools,
  assignedToolIds,
  onAssign,
  isLoading = false,
}: ToolAssignmentProps) {
  const [localAssignedIds, setLocalAssignedIds] = useState<string[]>(assignedToolIds);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const assignedTools = localAssignedIds
    .map((id) => availableTools.find((t) => t.id === id))
    .filter((t): t is Tool => !!t);

  const unassignedTools = availableTools.filter(
    (tool) => !localAssignedIds.includes(tool.id)
  );

  const filteredUnassignedTools = unassignedTools.filter((tool) =>
    tool.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setLocalAssignedIds((items) => {
        const oldIndex = items.indexOf(active.id as string);
        const newIndex = items.indexOf(over.id as string);
        return arrayMove(items, oldIndex, newIndex);
      });
    }

    setActiveId(null);
  };

  const handleAdd = (toolId: string) => {
    setLocalAssignedIds([...localAssignedIds, toolId]);
  };

  const handleRemove = (toolId: string) => {
    setLocalAssignedIds(localAssignedIds.filter((id) => id !== toolId));
  };

  const handleSave = () => {
    onAssign(localAssignedIds);
  };

  const hasChanges = JSON.stringify(localAssignedIds.sort()) !== JSON.stringify(assignedToolIds.sort());

  const activeTool = activeId
    ? availableTools.find((t) => t.id === activeId)
    : null;

  return (
    <div className="space-y-4">
      {/* Header with Save Button */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">
            Assign Tools to Agent
          </h3>
          <p className="text-sm text-text-secondary">
            Drag and drop tools to reorder, or click + to add
          </p>
        </div>
        <Button
          variant="primary"
          onClick={handleSave}
          isLoading={isLoading}
          disabled={!hasChanges || isLoading}
        >
          Save Changes
        </Button>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Assigned Tools (Left Column) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-text-primary">
              Assigned Tools ({assignedTools.length})
            </h4>
          </div>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={localAssignedIds}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2 min-h-[200px]">
                {assignedTools.length === 0 ? (
                  <div className="glass-card p-8 text-center">
                    <p className="text-text-secondary">
                      No tools assigned yet. Add tools from the available list.
                    </p>
                  </div>
                ) : (
                  assignedTools.map((tool) => (
                    <SortableToolItem
                      key={tool.id}
                      tool={tool}
                      onRemove={() => handleRemove(tool.id)}
                    />
                  ))
                )}
              </div>
            </SortableContext>

            <DragOverlay>
              {activeTool ? (
                <div className="glass-card p-3 flex items-center gap-3 opacity-80 shadow-lg">
                  <GripVertical className="w-5 h-5 text-text-secondary" />
                  <div className="flex-1">
                    <div className="font-medium text-text-primary">
                      {activeTool.name}
                    </div>
                  </div>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        </div>

        {/* Available Tools (Right Column) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-text-primary">
              Available Tools ({filteredUnassignedTools.length})
            </h4>
          </div>

          {/* Search */}
          <Input
            placeholder="Search tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />

          {/* Available Tools List */}
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {filteredUnassignedTools.length === 0 ? (
              <div className="glass-card p-8 text-center">
                <p className="text-text-secondary">
                  {searchQuery
                    ? 'No tools match your search'
                    : 'All tools are assigned'}
                </p>
              </div>
            ) : (
              filteredUnassignedTools.map((tool) => (
                <AvailableToolItem
                  key={tool.id}
                  tool={tool}
                  onAdd={() => handleAdd(tool.id)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
