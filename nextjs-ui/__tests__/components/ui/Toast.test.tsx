import { toast } from '@/components/ui/Toast';
import { toast as sonnerToast } from 'sonner';

// Mock sonner
jest.mock('sonner', () => ({
  toast: {
    custom: jest.fn(() => '12345'),
    dismiss: jest.fn(),
    loading: jest.fn(() => '67890'),
    promise: jest.fn(),
  },
}));

describe('Toast Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Variant Methods', () => {
    it('should call success toast with correct variant', () => {
      toast.success('Success message');

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          className: expect.stringContaining('border-green-500'),
        })
      );
    });

    it('should call error toast with correct variant', () => {
      toast.error('Error message');

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          className: expect.stringContaining('border-red-500'),
        })
      );
    });

    it('should call warning toast with correct variant', () => {
      toast.warning('Warning message');

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          className: expect.stringContaining('border-yellow-500'),
        })
      );
    });

    it('should call info toast with correct variant', () => {
      toast.info('Info message');

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          className: expect.stringContaining('border-blue-500'),
        })
      );
    });
  });

  describe('Options', () => {
    it('should pass description to sonner', () => {
      toast.success('Message', {
        description: 'This is a description',
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          description: 'This is a description',
        })
      );
    });

    it('should pass custom duration', () => {
      toast.success('Message', {
        duration: 10000,
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          duration: 10000,
        })
      );
    });

    it('should use default duration of 4000ms when not specified', () => {
      toast.success('Message');

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          duration: 4000,
        })
      );
    });

    it('should include cancel button when dismissible is true', () => {
      toast.success('Message', {
        dismissible: true,
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          cancel: expect.objectContaining({
            label: expect.anything(),
            onClick: expect.any(Function),
          }),
        })
      );
    });

    it('should NOT include cancel button when dismissible is false', () => {
      toast.success('Message', {
        dismissible: false,
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          cancel: undefined,
        })
      );
    });

    it('should include action button when action is provided', () => {
      const mockAction = jest.fn();

      toast.success('Message', {
        action: {
          label: 'Undo',
          onClick: mockAction,
        },
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          action: expect.objectContaining({
            label: 'Undo',
            onClick: expect.any(Function),
          }),
        })
      );
    });

    it('should call onDismiss when toast is dismissed', () => {
      const mockOnDismiss = jest.fn();

      toast.success('Message', {
        onDismiss: mockOnDismiss,
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          onDismiss: mockOnDismiss,
        })
      );
    });
  });

  describe('Custom Method', () => {
    it('should allow full custom configuration', () => {
      toast.custom({
        message: 'Custom message',
        description: 'Custom description',
        variant: 'warning',
        duration: 5000,
        dismissible: true,
        action: {
          label: 'Action',
          onClick: jest.fn(),
        },
        onDismiss: jest.fn(),
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          description: 'Custom description',
          duration: 5000,
          className: expect.stringContaining('border-yellow-500'),
          cancel: expect.any(Object),
          action: expect.any(Object),
          onDismiss: expect.any(Function),
        })
      );
    });

    it('should default to info variant when variant not specified', () => {
      toast.custom({
        message: 'Message',
      });

      expect(sonnerToast.custom).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          className: expect.stringContaining('border-blue-500'),
        })
      );
    });
  });

  describe('Utility Methods', () => {
    it('should call dismiss with toast ID', () => {
      toast.dismiss('12345');

      expect(sonnerToast.dismiss).toHaveBeenCalledWith('12345');
    });

    it('should call dismiss without ID to dismiss all', () => {
      toast.dismissAll();

      expect(sonnerToast.dismiss).toHaveBeenCalledWith();
    });

    it('should call loading with infinite duration', () => {
      toast.loading('Loading...');

      expect(sonnerToast.loading).toHaveBeenCalledWith('Loading...', {
        description: undefined,
        duration: Infinity,
      });
    });

    it('should call loading with description', () => {
      toast.loading('Loading...', {
        description: 'Please wait',
      });

      expect(sonnerToast.loading).toHaveBeenCalledWith('Loading...', {
        description: 'Please wait',
        duration: Infinity,
      });
    });

    it('should call promise with correct options', async () => {
      const mockPromise = Promise.resolve('data');

      toast.promise(mockPromise, {
        loading: 'Loading...',
        success: 'Success!',
        error: 'Failed!',
      });

      expect(sonnerToast.promise).toHaveBeenCalledWith(mockPromise, {
        loading: 'Loading...',
        success: 'Success!',
        error: 'Failed!',
      });
    });

    it('should call promise with function success handler', async () => {
      const mockPromise = Promise.resolve('data');
      const successHandler = (data: string) => `Loaded ${data}`;

      toast.promise(mockPromise, {
        loading: 'Loading...',
        success: successHandler,
        error: 'Failed!',
      });

      expect(sonnerToast.promise).toHaveBeenCalledWith(mockPromise, {
        loading: 'Loading...',
        success: successHandler,
        error: 'Failed!',
      });
    });
  });

  describe('Return Values', () => {
    it('should return toast ID from success', () => {
      const id = toast.success('Message');

      expect(id).toBe('12345');
    });

    it('should return toast ID from error', () => {
      const id = toast.error('Message');

      expect(id).toBe('12345');
    });

    it('should return toast ID from warning', () => {
      const id = toast.warning('Message');

      expect(id).toBe('12345');
    });

    it('should return toast ID from info', () => {
      const id = toast.info('Message');

      expect(id).toBe('12345');
    });

    it('should return toast ID from loading', () => {
      const id = toast.loading('Loading...');

      expect(id).toBe('67890');
    });
  });

  describe('Glassmorphism Styling', () => {
    it('should include glass-card class for all variants', () => {
      const variants = ['success', 'error', 'warning', 'info'] as const;

      variants.forEach((variant) => {
        toast[variant]('Message');

        expect(sonnerToast.custom).toHaveBeenCalledWith(
          expect.any(Function),
          expect.objectContaining({
            className: expect.stringContaining('glass-card'),
          })
        );
      });
    });

    it('should include variant-specific border classes', () => {
      const variantBorders = {
        success: 'border-green-500',
        error: 'border-red-500',
        warning: 'border-yellow-500',
        info: 'border-blue-500',
      };

      Object.entries(variantBorders).forEach(([variant, borderClass]) => {
        (toast as Record<string, (message: string) => void>)[variant]('Message');

        expect(sonnerToast.custom).toHaveBeenCalledWith(
          expect.any(Function),
          expect.objectContaining({
            className: expect.stringContaining(borderClass),
          })
        );
      });
    });
  });
});
