import type { Meta } from '@storybook/react';
import { toast, Toast } from './Toast';
import { Toaster } from 'sonner';

const meta: Meta = {
  title: 'UI/Toast',
  component: Toast,
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <div>
        <Story />
        <Toaster position="top-right" richColors closeButton />
      </div>
    ),
  ],
};

export default meta;

export const Success = {
  render: () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Success Toasts</h3>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => toast.success('Profile updated successfully!')}
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Simple Success
        </button>
        <button
          onClick={() =>
            toast.success('Changes saved', {
              description: 'Your profile has been updated.',
            })
          }
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          With Description
        </button>
        <button
          onClick={() =>
            toast.success('File uploaded', {
              description: 'document.pdf (2.5 MB)',
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Dismissible
        </button>
        <button
          onClick={() =>
            toast.success('Account created', {
              duration: 10000,
            })
          }
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Long Duration (10s)
        </button>
      </div>
    </div>
  ),
};

export const ErrorToast = {
  render: () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Error Toasts</h3>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => toast.error('Failed to save changes')}
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          Simple Error
        </button>
        <button
          onClick={() =>
            toast.error('Network error', {
              description: 'Unable to connect to the server. Please try again.',
            })
          }
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          With Description
        </button>
        <button
          onClick={() =>
            toast.error('Upload failed', {
              description: 'File size exceeds 10 MB limit',
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          Dismissible
        </button>
        <button
          onClick={() =>
            toast.error('Critical error', {
              description: 'Please contact support if this persists.',
              duration: Infinity,
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          Persistent (Manual Dismiss)
        </button>
      </div>
    </div>
  ),
};

export const Warning = {
  render: () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Warning Toasts</h3>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => toast.warning('Your session will expire soon')}
          className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
        >
          Simple Warning
        </button>
        <button
          onClick={() =>
            toast.warning('Unsaved changes', {
              description: 'You have unsaved changes that will be lost.',
            })
          }
          className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
        >
          With Description
        </button>
        <button
          onClick={() =>
            toast.warning('Storage almost full', {
              description: '90% of your storage is used (9/10 GB)',
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
        >
          Dismissible
        </button>
      </div>
    </div>
  ),
};

export const Info = {
  render: () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Info Toasts</h3>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => toast.info('New version available')}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Simple Info
        </button>
        <button
          onClick={() =>
            toast.info('Scheduled maintenance', {
              description: 'System will be down on Sunday 2 AM - 4 AM',
            })
          }
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          With Description
        </button>
        <button
          onClick={() =>
            toast.info('Tip of the day', {
              description: 'You can use keyboard shortcuts to navigate faster!',
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Dismissible
        </button>
      </div>
    </div>
  ),
};

export const WithAction = {
  render: () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Toasts with Actions</h3>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() =>
            toast.success('Message sent', {
              action: {
                label: 'Undo',
                onClick: () => alert('Message unsent!'),
              },
            })
          }
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Success with Undo
        </button>
        <button
          onClick={() =>
            toast.warning('Session expiring', {
              description: 'Your session will expire in 2 minutes',
              action: {
                label: 'Extend Session',
                onClick: () => alert('Session extended!'),
              },
              duration: 8000,
            })
          }
          className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
        >
          Warning with Action
        </button>
        <button
          onClick={() =>
            toast.info('New feature available', {
              description: 'Check out our new dark mode!',
              action: {
                label: 'Try Now',
                onClick: () => alert('Opening settings...'),
              },
              dismissible: true,
            })
          }
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Info with Action
        </button>
      </div>
    </div>
  ),
};

export const Loading = {
  render: () => {
    const handleAsyncOperation = () => {
      const loadingId = toast.loading('Processing request...');

      setTimeout(() => {
        toast.dismiss(loadingId);
        toast.success('Request completed!');
      }, 3000);
    };

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Loading Toasts</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => toast.loading('Loading data...')}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Infinite Loading
          </button>
          <button
            onClick={() =>
              toast.loading('Uploading file...', {
                description: 'This may take a few moments',
              })
            }
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Loading with Description
          </button>
          <button
            onClick={handleAsyncOperation}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Async Operation (3s)
          </button>
        </div>
      </div>
    );
  },
};

export const PromiseToast = {
  render: () => {
    const simulateApiCall = () => {
      return new globalThis.Promise<string>((resolve, reject) => {
        setTimeout(() => {
          if (Math.random() > 0.5) {
            resolve('Data loaded!');
          } else {
            reject(new globalThis.Error('Network error'));
          }
        }, 2000);
      });
    };

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Promise-Based Toasts</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() =>
              toast.promise(simulateApiCall(), {
                loading: 'Fetching data...',
                success: 'Data loaded successfully!',
                error: 'Failed to fetch data',
              })
            }
            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
          >
            Promise Toast (Random)
          </button>
          <button
            onClick={() =>
              toast.promise(Promise.resolve('User data'), {
                loading: 'Saving...',
                success: (data) => `${data} saved successfully!`,
                error: (err) => `Error: ${err.message}`,
              })
            }
            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
          >
            Promise with Functions
          </button>
        </div>
      </div>
    );
  },
};

export const Dismiss = {
  render: () => {
    const showMultipleToasts = () => {
      toast.info('Toast 1');
      setTimeout(() => toast.info('Toast 2'), 100);
      setTimeout(() => toast.info('Toast 3'), 200);
      setTimeout(() => toast.info('Toast 4'), 300);
    };

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Dismiss Toasts</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={showMultipleToasts}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Show Multiple Toasts
          </button>
          <button
            onClick={() => toast.dismissAll()}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Dismiss All
          </button>
          <button
            onClick={() => {
              const id = toast.info('This toast will auto-dismiss in 2s', {
                duration: 10000,
              });
              setTimeout(() => toast.dismiss(id), 2000);
            }}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Programmatic Dismiss
          </button>
        </div>
      </div>
    );
  },
};

export const Showcase = {
  render: () => {
    const scenarios = [
      {
        label: 'File Upload Success',
        action: () =>
          toast.success('File uploaded', {
            description: 'document.pdf (2.5 MB)',
            action: {
              label: 'View',
              onClick: () => alert('Opening file...'),
            },
            dismissible: true,
          }),
      },
      {
        label: 'API Error',
        action: () =>
          toast.error('Request failed', {
            description: 'Server returned 500 Internal Server Error',
            action: {
              label: 'Retry',
              onClick: () => alert('Retrying...'),
            },
            dismissible: true,
          }),
      },
      {
        label: 'Session Warning',
        action: () =>
          toast.warning('Session expiring soon', {
            description: 'You will be logged out in 5 minutes',
            action: {
              label: 'Stay Logged In',
              onClick: () => alert('Session extended'),
            },
            duration: 8000,
          }),
      },
      {
        label: 'Update Available',
        action: () =>
          toast.info('New version available', {
            description: 'Version 2.0 with new features!',
            action: {
              label: 'Update Now',
              onClick: () => alert('Updating...'),
            },
            dismissible: true,
          }),
      },
      {
        label: 'Async Operation',
        action: () => {
          toast.promise(
            new Promise((resolve) => setTimeout(() => resolve('Complete!'), 3000)),
            {
              loading: 'Processing...',
              success: 'Operation completed!',
              error: 'Operation failed',
            }
          );
        },
      },
    ];

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold mb-4">Toast Showcase</h3>
        <p className="text-sm text-gray-600 mb-4">
          Click buttons to see different toast variations in action
        </p>
        <div className="grid grid-cols-2 gap-3">
          {scenarios.map((scenario, idx) => (
            <button
              key={idx}
              onClick={scenario.action}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg text-left transition-colors"
            >
              <div className="font-medium">{scenario.label}</div>
            </button>
          ))}
        </div>
      </div>
    );
  },
};
