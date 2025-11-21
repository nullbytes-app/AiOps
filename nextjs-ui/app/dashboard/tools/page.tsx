'use client';

/**
 * Add Tool Page (/tools)
 * OpenAPI spec upload, validation, preview, and import
 * RBAC: tenant_admin + developer (can import), operator + viewer (redirect)
 */

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import yaml from 'js-yaml';
import type { OpenAPIOperation, ParsedSpec } from '@/lib/api/tools';
import { useImportTools } from '@/lib/hooks/useTools';
import { OpenAPIUpload } from '@/components/tools/OpenAPIUpload';
import { ToolPreview } from '@/components/tools/ToolPreview';
import { ImportConfig } from '@/components/tools/ImportConfig';
import { Button } from '@/components/ui/Button';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';

type Step = 'upload' | 'validation' | 'preview' | 'import';

export default function ToolsPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const importMutation = useImportTools();

  const [step, setStep] = useState<Step>('upload');
  const [fileName, setFileName] = useState<string>('');
  const [parsedSpec, setParsedSpec] = useState<ParsedSpec | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [selectedOperations, setSelectedOperations] = useState<string[]>([]);

  const userRole = session?.user?.role || 'viewer';
  const canImport = ['tenant_admin', 'developer'].includes(userRole);

  // Redirect if no permission
  useEffect(() => {
    if (session && !canImport) {
      router.push('/dashboard');
    }
  }, [session, canImport, router]);

  const parseOpenAPISpec = (content: string, fileType: 'json' | 'yaml'): ParsedSpec | null => {
    try {
      // Parse content
      let spec: Record<string, unknown>;
      if (fileType === 'json') {
        spec = JSON.parse(content);
      } else {
        spec = yaml.load(content) as Record<string, unknown>;
      }

      // Basic validation for OpenAPI structure
      if (!spec.openapi && !spec.swagger) {
        throw new Error('Not a valid OpenAPI spec (missing openapi/swagger field)');
      }

      if (!spec.paths || typeof spec.paths !== 'object') {
        throw new Error('Invalid spec: missing paths object');
      }

      // Extract operations
      const operations: OpenAPIOperation[] = [];
      const paths = spec.paths as Record<string, Record<string, unknown>>;

      for (const [path, pathItem] of Object.entries(paths)) {
        if (!pathItem || typeof pathItem !== 'object') continue;

        for (const [method, operation] of Object.entries(pathItem)) {
          const httpMethod = method.toUpperCase();
          if (!['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].includes(httpMethod)) {
            continue;
          }

          if (typeof operation !== 'object' || operation === null) continue;

          const op = operation as Record<string, unknown>;
          const operationId =
            (op.operationId as string) || `${method}_${path.replace(/\//g, '_')}`;

          operations.push({
            method: httpMethod,
            path,
            operationId,
            summary: (op.summary as string) || '',
            description: (op.description as string) || undefined,
            parameters: Array.isArray(op.parameters)
              ? op.parameters.map((p: unknown) => {
                  const param = p as Record<string, unknown>;
                  return {
                    name: (param.name as string) || '',
                    in: (param.in as 'query' | 'path' | 'header' | 'cookie') || 'query',
                    required: Boolean(param.required),
                    schema: (param.schema as Record<string, unknown>) || {},
                    description: (param.description as string) || undefined,
                  };
                })
              : [],
            requestBody: op.requestBody as Record<string, unknown> | undefined,
            responses: op.responses as Record<string, unknown> | undefined,
          });
        }
      }

      if (operations.length === 0) {
        throw new Error('No valid operations found in spec');
      }

      return { spec, operations };
    } catch (err) {
      throw new Error(
        `Failed to parse spec: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    }
  };

  const handleFileSelect = (file: File, content: string) => {
    setFileName(file.name);
    setStep('validation');
    setValidationError(null);

    try {
      const fileType = file.name.endsWith('.json') ? 'json' : 'yaml';
      const parsed = parseOpenAPISpec(content, fileType);

      if (!parsed) {
        throw new Error('Failed to parse specification');
      }

      setParsedSpec(parsed);
      setSelectedOperations(parsed.operations.map((op) => op.operationId));
      setStep('preview');
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : 'Validation failed');
      setStep('validation');
    }
  };

  const handleImport = async (config: {
    namePrefix?: string;
    baseUrl: string;
    authConfig: { type: 'none' | 'api_key' | 'bearer' | 'basic' };
  }) => {
    if (!parsedSpec) return;

    await importMutation.mutateAsync({
      spec: parsedSpec.spec,
      selected_operations: selectedOperations,
      name_prefix: config.namePrefix,
      base_url: config.baseUrl,
      auth_config: config.authConfig,
    });

    // Redirect to agents config page for tool assignment
    router.push('/dashboard/agents-config');
  };

  if (!canImport) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-sm text-yellow-800">
            You do not have permission to import tools.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Import Tools from OpenAPI</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload an OpenAPI spec to automatically generate tools for agent use
        </p>
      </div>

      {/* Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {(['upload', 'validation', 'preview', 'import'] as const).map((s, idx) => (
            <div key={s} className="flex items-center">
              <div
                className={`
                  flex items-center justify-center w-8 h-8 rounded-full border-2
                  ${
                    step === s
                      ? 'border-accent-blue bg-accent-blue text-white'
                      : idx < ['upload', 'validation', 'preview', 'import'].indexOf(step)
                        ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                        : 'border-gray-300 bg-white text-gray-400'
                  }
                `}
              >
                {idx + 1}
              </div>
              {idx < 3 && (
                <div
                  className={`h-0.5 w-24 mx-2 ${
                    idx < ['upload', 'validation', 'preview', 'import'].indexOf(step)
                      ? 'bg-accent-blue'
                      : 'bg-gray-300'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2">
          {['Upload', 'Validate', 'Preview', 'Import'].map((label) => (
            <span key={label} className="text-xs text-gray-600 w-24 text-center">
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Upload Step */}
      {step === 'upload' && (
        <div className="space-y-4">
          <OpenAPIUpload onFileSelect={handleFileSelect} />
        </div>
      )}

      {/* Validation Step */}
      {step === 'validation' && (
        <div className="space-y-4">
          <div
            className={`p-6 rounded-lg border-2 ${
              validationError
                ? 'border-red-300 bg-red-50'
                : 'border-accent-blue bg-accent-blue/5'
            }`}
          >
            <div className="flex items-start gap-3">
              {validationError ? (
                <XCircle className="h-6 w-6 text-red-600 shrink-0" />
              ) : (
                <AlertCircle className="h-6 w-6 text-accent-blue shrink-0 animate-pulse" />
              )}
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {validationError ? 'Validation Failed' : 'Validating Spec...'}
                </h3>
                <p className="text-sm text-gray-600">
                  {validationError || 'Parsing and validating OpenAPI specification'}
                </p>
              </div>
            </div>
          </div>

          {validationError && (
            <Button onClick={() => setStep('upload')}>Upload Different File</Button>
          )}
        </div>
      )}

      {/* Preview Step */}
      {step === 'preview' && parsedSpec && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-900">Valid OpenAPI Spec</p>
              <p className="text-xs text-green-700">
                Found {parsedSpec.operations.length} operation(s) in {fileName}
              </p>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Select Operations to Import
            </h3>
            <ToolPreview
              operations={parsedSpec.operations}
              selectedOperations={selectedOperations}
              onSelectionChange={setSelectedOperations}
            />
          </div>

          <div className="flex justify-between pt-4 border-t">
            <Button variant="secondary" onClick={() => setStep('upload')}>
              Upload Different File
            </Button>
            <Button
              onClick={() => setStep('import')}
              disabled={selectedOperations.length === 0}
            >
              Continue to Import ({selectedOperations.length} selected)
            </Button>
          </div>
        </div>
      )}

      {/* Import Step */}
      {step === 'import' && parsedSpec && (
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Configure Import
            </h3>
            <ImportConfig
              onSubmit={handleImport}
              isLoading={importMutation.isPending}
            />
          </div>

          <div className="flex justify-start pt-4 border-t">
            <Button variant="secondary" onClick={() => setStep('preview')}>
              Back to Preview
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
