'use client';

/**
 * PromptEditor - CodeMirror editor with split-pane layout
 * Left pane (60%): Editor with line numbers, syntax highlighting
 * Right pane (40%): Preview with variable substitution
 */

import { useState, useEffect } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { EditorView } from '@codemirror/view';
import { extractVariables } from '@/lib/api/prompts';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave: () => void;
  onRevert?: () => void;
  isSubmitting?: boolean;
}

export function PromptEditor({
  value,
  onChange,
  onSave,
  onRevert,
  isSubmitting = false,
}: PromptEditorProps) {
  const [detectedVariables, setDetectedVariables] = useState<string[]>([]);
  const [testData, setTestData] = useState<Record<string, string>>({});
  const [previewText, setPreviewText] = useState<string>('');

  // Extract variables from template
  useEffect(() => {
    const variables = extractVariables(value);
    setDetectedVariables(variables);

    // Initialize test data with empty strings for new variables
    setTestData((prev) => {
      const newData = { ...prev };
      variables.forEach((variable) => {
        if (!(variable in newData)) {
          newData[variable] = '';
        }
      });
      return newData;
    });
  }, [value]);

  // Generate preview with substituted variables
  useEffect(() => {
    let preview = value;
    Object.entries(testData).forEach(([key, val]) => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
      preview = preview.replace(regex, val || `{{${key}}}`);
    });
    setPreviewText(preview);
  }, [value, testData]);

  const handleVariableChange = (variable: string, val: string) => {
    setTestData((prev) => ({ ...prev, [variable]: val }));
  };

  return (
    <div className="flex flex-col md:flex-row gap-4 h-full">
      {/* Editor Pane (60%) */}
      <div className="flex-1 md:w-3/5 flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <Label className="text-sm font-medium">Template Editor</Label>
          <div className="flex gap-2">
            {onRevert && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onRevert}
                disabled={isSubmitting}
              >
                Revert
              </Button>
            )}
            <Button size="sm" onClick={onSave} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>

        <div className="border border-gray-200 rounded-md overflow-hidden flex-1">
          <CodeMirror
            value={value}
            height="100%"
            minHeight="400px"
            extensions={[EditorView.lineWrapping]}
            onChange={onChange}
            placeholder="# System Prompt Template
# Available variables: {{agent_name}}, {{ticket_id}}, {{user_name}}

You are {{agent_name}}, an AI assistant helping with ticket {{ticket_id}}."
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              foldGutter: true,
              autocompletion: true,
            }}
            className="codemirror-editor"
          />
        </div>

        {detectedVariables.length > 0 && (
          <div className="mt-2 text-xs text-gray-500">
            Detected variables: {detectedVariables.join(', ')}
          </div>
        )}
      </div>

      {/* Preview Pane (40%) */}
      <div className="flex-1 md:w-2/5 flex flex-col">
        <Label className="text-sm font-medium mb-2">Preview with Test Data</Label>

        {/* Test Data Inputs */}
        {detectedVariables.length > 0 && (
          <div className="mb-4 space-y-2 p-4 bg-gray-50 rounded-md">
            <p className="text-xs font-medium text-gray-700 mb-2">
              Test Variables:
            </p>
            {detectedVariables.map((variable) => (
              <div key={variable}>
                <Label htmlFor={`var-${variable}`} className="text-xs">
                  {variable}
                </Label>
                <Input
                  id={`var-${variable}`}
                  value={testData[variable] || ''}
                  onChange={(e) => handleVariableChange(variable, e.target.value)}
                  placeholder={`Enter ${variable}`}
                  className="mt-1"
                />
              </div>
            ))}
          </div>
        )}

        {/* Preview Output */}
        <div className="flex-1 border border-gray-200 rounded-md p-4 bg-white overflow-auto">
          <p className="text-xs font-medium text-gray-700 mb-2">Rendered Output:</p>
          <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
            {previewText || 'Start typing to see preview...'}
          </pre>
        </div>
      </div>
    </div>
  );
}
