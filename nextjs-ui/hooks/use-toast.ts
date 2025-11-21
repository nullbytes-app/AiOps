// Simple toast hook using existing Toast component
import { useState, useCallback } from 'react';

type ToastVariant = 'default' | 'destructive';

interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

let toastListeners: Array<(toast: ToastOptions) => void> = [];

export function useToast() {
  const [, forceUpdate] = useState(0);

  const toast = useCallback((options: ToastOptions) => {
    toastListeners.forEach((listener) => listener(options));
  }, []);

  const subscribe = useCallback((listener: (toast: ToastOptions) => void) => {
    toastListeners.push(listener);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== listener);
    };
  }, []);

  return {
    toast,
    subscribe,
  };
}
