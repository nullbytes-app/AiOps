/**
 * Queue Pause/Resume Toggle Component
 *
 * Glassmorphic toggle button for pausing/resuming queue processing.
 * - Only visible to tenant_admin and operator roles
 * - Confirmation dialog for pause action
 * - Optimistic UI updates
 * - Toast notifications for success/failure
 *
 * Reference: Story 5, AC-1
 */

'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { Loader2, Pause, Play, AlertTriangle } from 'lucide-react';
import { useQueueStatus, usePauseQueue, useResumeQueue } from '@/lib/hooks/useQueue';

/**
 * Check if user has permission to pause/resume queue
 */
const canManageQueue = (role?: string): boolean => {
  return role === 'tenant_admin' || role === 'operator';
};

export function QueuePauseToggle() {
  const { data: session } = useSession();
  const { data: status, isLoading } = useQueueStatus();
  const pauseMutation = usePauseQueue();
  const resumeMutation = useResumeQueue();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // Hide if user doesn't have permission
  if (!canManageQueue(session?.user?.role)) {
    return null;
  }

  if (isLoading || !status) {
    return (
      <div className="glass-card px-4 py-2">
        <Loader2 className="w-5 h-5 animate-spin text-text-secondary" />
      </div>
    );
  }

  const handlePause = () => {
    setShowConfirmDialog(true);
  };

  const confirmPause = () => {
    pauseMutation.mutate(undefined, {
      onSuccess: () => {
        setShowConfirmDialog(false);
      },
    });
  };

  const handleResume = () => {
    resumeMutation.mutate();
  };

  const isProcessing = pauseMutation.isPending || resumeMutation.isPending;

  return (
    <>
      <button
        onClick={status.is_paused ? handleResume : handlePause}
        disabled={isProcessing}
        className="glass-card px-6 py-3 flex items-center gap-2 hover:bg-white/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label={status.is_paused ? 'Resume queue' : 'Pause queue'}
      >
        {isProcessing ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : status.is_paused ? (
          <Play className="w-5 h-5 text-accent-green" />
        ) : (
          <Pause className="w-5 h-5 text-accent-orange" />
        )}
        <span className="font-medium text-text-primary">
          {isProcessing
            ? status.is_paused
              ? 'Resuming...'
              : 'Pausing...'
            : status.is_paused
            ? '▶️ Resume Queue'
            : '⏸️ Pause Queue'}
        </span>
      </button>

      {/* Confirmation Dialog */}
      <Transition appear show={showConfirmDialog} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setShowConfirmDialog(false)}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4 text-center">
              <Transition.Child
                as={Fragment}
                enter="ease-out duration-300"
                enterFrom="opacity-0 scale-95"
                enterTo="opacity-100 scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 scale-100"
                leaveTo="opacity-0 scale-95"
              >
                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl glass-card p-6 text-left align-middle shadow-xl transition-all">
                  <Dialog.Title
                    as="h3"
                    className="text-lg font-medium leading-6 text-text-primary flex items-center gap-2"
                  >
                    <AlertTriangle className="w-5 h-5 text-accent-orange" />
                    Pause Queue Processing?
                  </Dialog.Title>
                  <div className="mt-2">
                    <p className="text-sm text-text-secondary">
                      This will stop processing new tasks from the queue. Tasks currently being
                      processed will continue to completion.
                    </p>
                    <p className="text-sm text-text-secondary mt-2 font-medium">
                      Continue?
                    </p>
                  </div>

                  <div className="mt-6 flex gap-3 justify-end">
                    <button
                      type="button"
                      className="px-4 py-2 text-sm font-medium text-text-primary bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                      onClick={() => setShowConfirmDialog(false)}
                      disabled={pauseMutation.isPending}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="px-4 py-2 text-sm font-medium text-white bg-accent-orange hover:bg-accent-orange/90 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                      onClick={confirmPause}
                      disabled={pauseMutation.isPending}
                    >
                      {pauseMutation.isPending && (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      )}
                      Pause Queue
                    </button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </>
  );
}
