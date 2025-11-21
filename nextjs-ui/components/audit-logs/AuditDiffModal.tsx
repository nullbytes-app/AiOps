/**
 * Audit Diff Modal Component
 *
 * Displays a side-by-side visual diff of JSON changes using jsondiffpatch.
 * Shows old_value vs new_value with color coding:
 * - Red: Removed fields
 * - Green: Added fields
 * - Yellow: Modified fields
 */

'use client';

import { useEffect, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { X } from 'lucide-react';
import * as jsondiffpatch from 'jsondiffpatch';
import { useAuditDiff } from '@/lib/hooks/useAudit';
import { Loading } from '@/components/ui/Loading';

// Import jsondiffpatch HTML styles
import 'jsondiffpatch/formatters/styles/html.css';

interface AuditDiffModalProps {
  /** Audit log entry ID to fetch diff for */
  auditLogId: string | null;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
}

/**
 * Modal component for displaying audit log diffs
 *
 * @example
 * ```tsx
 * const [selectedId, setSelectedId] = useState<string | null>(null);
 *
 * <AuditDiffModal
 *   auditLogId={selectedId}
 *   isOpen={!!selectedId}
 *   onClose={() => setSelectedId(null)}
 * />
 * ```
 */
export function AuditDiffModal({
  auditLogId,
  isOpen,
  onClose,
}: AuditDiffModalProps) {
  const diffContainerRef = useRef<HTMLDivElement>(null);
  const { data: diff, isLoading, error } = useAuditDiff(auditLogId);

  // Generate HTML diff when data is loaded
  useEffect(() => {
    if (!diff || !diffContainerRef.current) return;

    // Import formatters dynamically
    import('jsondiffpatch/formatters/html').then((htmlFormatter) => {
      const differ = jsondiffpatch.create({
        objectHash: (obj: object) => {
          const record = obj as Record<string, unknown>;
          return (
            (record?.id as string) ||
            (record?.name as string) ||
            JSON.stringify(obj)
          );
        },
        arrays: {
          detectMove: true,
          includeValueOnMove: false,
        },
      });

      // Calculate delta
      const delta = differ.diff(diff.old_value, diff.new_value);

      if (delta && diffContainerRef.current) {
        // Format as HTML
        const htmlDiff = htmlFormatter.format(delta, diff.old_value);
        diffContainerRef.current.innerHTML =
          htmlDiff || '<p class="text-muted-foreground">No changes detected</p>';
      } else if (diffContainerRef.current) {
        diffContainerRef.current.innerHTML =
          '<p class="text-muted-foreground">No changes detected</p>';
      }
    });
  }, [diff]);

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" />
        </Transition.Child>

        {/* Modal content */}
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-lg border border-border bg-card p-6 text-left align-middle shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold text-foreground">
                    Audit Log Changes
                  </Dialog.Title>
                  <button
                    type="button"
                    className="rounded-md text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <X className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                {/* Metadata */}
                {diff && (
                  <div className="mb-4 space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center space-x-4">
                      <span>
                        <span className="font-medium">Action:</span>{' '}
                        <span className="capitalize">{diff.action}</span>
                      </span>
                      <span>
                        <span className="font-medium">Entity:</span>{' '}
                        {diff.entity_type}
                      </span>
                      <span>
                        <span className="font-medium">User:</span>{' '}
                        {diff.user_email}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Timestamp:</span>{' '}
                      {new Date(diff.created_at).toLocaleString()}
                    </div>
                  </div>
                )}

                {/* Diff Content */}
                <div className="border border-border rounded-lg bg-muted/30 p-4 overflow-auto max-h-[60vh]">
                  {isLoading && (
                    <div className="flex items-center justify-center py-12">
                      <Loading size="lg" />
                    </div>
                  )}

                  {error && (
                    <div className="text-destructive text-center py-8">
                      <p className="font-medium">Failed to load diff</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {error.message}
                      </p>
                    </div>
                  )}

                  {/* jsondiffpatch HTML output */}
                  <div
                    ref={diffContainerRef}
                    className="jsondiffpatch-diff"
                    style={{
                      fontSize: '14px',
                      fontFamily: 'var(--font-mono)',
                    }}
                  />
                </div>

                {/* Footer */}
                <div className="mt-6 flex justify-end">
                  <button
                    type="button"
                    className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    onClick={onClose}
                  >
                    Close
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
