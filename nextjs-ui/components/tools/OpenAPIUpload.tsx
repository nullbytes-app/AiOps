'use client';

/**
 * OpenAPIUpload - Drag-and-drop file upload for OpenAPI specs
 * Accepts: .json, .yaml, .yml files (max 5MB)
 * Features: File validation, multiple file support, preview
 */

import { useState, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '@/lib/utils/cn';

interface UploadedFile {
  file: File;
  content: string;
  error?: string;
}

interface OpenAPIUploadProps {
  onFileSelect: (file: File, content: string) => void;
  isLoading?: boolean;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_EXTENSIONS = ['.json', '.yaml', '.yml'];

export function OpenAPIUpload({ onFileSelect, isLoading = false }: OpenAPIUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`;
    }

    // Check file extension
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      return `Invalid file type. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`;
    }

    return null;
  };

  const handleFile = useCallback(
    async (file: File) => {
      const error = validateFile(file);
      if (error) {
        setUploadedFile({ file, content: '', error });
        return;
      }

      try {
        const content = await file.text();
        setUploadedFile({ file, content });
        onFileSelect(file, content);
      } catch {
        setUploadedFile({
          file,
          content: '',
          error: 'Failed to read file content',
        });
      }
    },
    [onFileSelect]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      e.preventDefault();
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    },
    [handleFile]
  );

  const handleRemove = () => {
    setUploadedFile(null);
  };

  return (
    <div className="space-y-4">
      {/* Upload Zone */}
      {!uploadedFile && (
        <div
          className={cn(
            'relative border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            dragActive
              ? 'border-accent-blue bg-accent-blue/5'
              : 'border-gray-300 hover:border-accent-blue/50',
            isLoading && 'opacity-50 pointer-events-none'
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            className="sr-only"
            accept={ACCEPTED_EXTENSIONS.join(',')}
            onChange={handleChange}
            disabled={isLoading}
          />

          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />

          <label
            htmlFor="file-upload"
            className="cursor-pointer text-sm font-medium text-gray-700"
          >
            <span className="text-accent-blue hover:text-accent-blue/80">
              Click to browse
            </span>{' '}
            or drag and drop
          </label>

          <p className="text-xs text-gray-500 mt-2">
            OpenAPI spec (.json, .yaml, .yml) up to 5MB
          </p>
        </div>
      )}

      {/* File Preview */}
      {uploadedFile && (
        <div
          className={cn(
            'border rounded-lg p-4',
            uploadedFile.error ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-gray-50'
          )}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {uploadedFile.file.name}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {(uploadedFile.file.size / 1024).toFixed(2)} KB
                </p>

                {uploadedFile.error && (
                  <div className="flex items-center gap-2 mt-2 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    <span>{uploadedFile.error}</span>
                  </div>
                )}
              </div>
            </div>

            {!isLoading && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRemove}
                className="shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
