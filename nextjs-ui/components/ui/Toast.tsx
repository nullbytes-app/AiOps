import { toast as sonnerToast, ExternalToast } from 'sonner';
import { CheckCircle2, XCircle, AlertCircle, Info, X } from 'lucide-react';

export interface ToastProps {
  /**
   * Toast message content
   */
  message: string;
  /**
   * Toast description (optional secondary text)
   */
  description?: string;
  /**
   * Toast variant: success, error, warning, info
   */
  variant?: 'success' | 'error' | 'warning' | 'info';
  /**
   * Duration in milliseconds (default: 4000ms)
   * Set to Infinity to keep toast open indefinitely
   */
  duration?: number;
  /**
   * Show close button (default: false)
   */
  dismissible?: boolean;
  /**
   * Custom action button
   */
  action?: {
    label: string;
    onClick: () => void;
  };
  /**
   * Callback when toast is dismissed
   */
  onDismiss?: () => void;
}

const variantConfig = {
  success: {
    icon: CheckCircle2,
    className: 'border-green-500 bg-green-50 dark:bg-green-900/20',
    iconColor: 'text-green-600 dark:text-green-400',
  },
  error: {
    icon: XCircle,
    className: 'border-red-500 bg-red-50 dark:bg-red-900/20',
    iconColor: 'text-red-600 dark:text-red-400',
  },
  warning: {
    icon: AlertCircle,
    className: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
    iconColor: 'text-yellow-600 dark:text-yellow-400',
  },
  info: {
    icon: Info,
    className: 'border-blue-500 bg-blue-50 dark:bg-blue-900/20',
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
};

/**
 * Toast notification component using Sonner
 *
 * Provides accessible, customizable toast notifications with:
 * - 4 variants (success, error, warning, info)
 * - Optional description text
 * - Customizable duration
 * - Dismissible option
 * - Action button support
 * - Keyboard navigation (Escape to dismiss)
 * - ARIA live regions for screen readers
 *
 * @example
 * ```tsx
 * import { toast } from '@/components/ui/Toast';
 *
 * // Success toast
 * toast.success('Profile updated successfully!');
 *
 * // Error toast with description
 * toast.error('Failed to save changes', {
 *   description: 'Please try again later.'
 * });
 *
 * // Warning with action button
 * toast.warning('Your session will expire soon', {
 *   action: {
 *     label: 'Extend',
 *     onClick: () => extendSession()
 *   }
 * });
 *
 * // Custom toast
 * toast.custom({
 *   message: 'Custom notification',
 *   variant: 'info',
 *   duration: 5000,
 *   dismissible: true
 * });
 * ```
 */
export const toast = {
  /**
   * Show a success toast
   */
  success: (message: string, options?: Omit<ToastProps, 'message' | 'variant'>) => {
    return showToast({ message, variant: 'success', ...options });
  },

  /**
   * Show an error toast
   */
  error: (message: string, options?: Omit<ToastProps, 'message' | 'variant'>) => {
    return showToast({ message, variant: 'error', ...options });
  },

  /**
   * Show a warning toast
   */
  warning: (message: string, options?: Omit<ToastProps, 'message' | 'variant'>) => {
    return showToast({ message, variant: 'warning', ...options });
  },

  /**
   * Show an info toast
   */
  info: (message: string, options?: Omit<ToastProps, 'message' | 'variant'>) => {
    return showToast({ message, variant: 'info', ...options });
  },

  /**
   * Show a custom toast with full configuration
   */
  custom: (props: ToastProps) => {
    return showToast(props);
  },

  /**
   * Dismiss a specific toast by ID
   */
  dismiss: (toastId?: string | number) => {
    sonnerToast.dismiss(toastId);
  },

  /**
   * Dismiss all active toasts
   */
  dismissAll: () => {
    sonnerToast.dismiss();
  },

  /**
   * Show a loading toast (infinite duration)
   */
  loading: (message: string, options?: Omit<ToastProps, 'message' | 'variant' | 'duration'>) => {
    return sonnerToast.loading(message, {
      description: options?.description,
      duration: Infinity,
    });
  },

  /**
   * Promise-based toast for async operations
   *
   * @example
   * ```tsx
   * toast.promise(saveProfile(), {
   *   loading: 'Saving profile...',
   *   success: 'Profile saved!',
   *   error: 'Failed to save profile'
   * });
   * ```
   */
  promise: <T,>(
    promise: Promise<T>,
    options: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: Error) => string);
      description?: string;
    }
  ) => {
    return sonnerToast.promise(promise, options);
  },
};

/**
 * Internal helper to show toast with custom rendering
 */
function showToast(props: ToastProps): string | number {
  const {
    message,
    description,
    variant = 'info',
    duration = 4000,
    dismissible = false,
    action,
    onDismiss,
  } = props;

  const config = variantConfig[variant];
  const Icon = config.icon;

  const sonnerOptions: ExternalToast = {
    duration,
    onDismiss,
    className: `glass-card border-2 ${config.className}`,
    description,
    cancel: dismissible
      ? {
          label: <X size={16} />,
          onClick: () => {},
        }
      : undefined,
    action: action
      ? {
          label: action.label,
          onClick: action.onClick,
        }
      : undefined,
  };

  return sonnerToast.custom(
    (t) => (
      <div className="flex items-start gap-3 p-4 w-full">
        <Icon size={20} className={`flex-shrink-0 ${config.iconColor}`} />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 dark:text-white">{message}</div>
          {description && (
            <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</div>
          )}
          {action && (
            <button
              onClick={() => {
                action.onClick();
                sonnerToast.dismiss(t);
              }}
              className="mt-2 px-3 py-1.5 text-sm font-medium rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              {action.label}
            </button>
          )}
        </div>
        {dismissible && (
          <button
            onClick={() => sonnerToast.dismiss(t)}
            className="flex-shrink-0 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            aria-label="Dismiss notification"
          >
            <X size={16} className="text-gray-500 dark:text-gray-400" />
          </button>
        )}
      </div>
    ),
    sonnerOptions
  );
}

/**
 * Toast component (for Storybook and testing)
 *
 * Note: This is a utility component, not a React component to render.
 * Use the `toast` API instead:
 *
 * @example
 * ```tsx
 * import { toast } from '@/components/ui/Toast';
 * toast.success('Success message');
 * ```
 */
export const Toast = () => null;
