import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OpenAPIUpload } from '@/components/tools/OpenAPIUpload';

const mockOnFileSelect = jest.fn();

describe('OpenAPIUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Upload zone rendering', () => {
    it('renders upload zone with instructions', () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      expect(screen.getByText(/Click to browse/)).toBeInTheDocument();
      expect(screen.getByText(/or drag and drop/)).toBeInTheDocument();
      expect(
        screen.getByText(/OpenAPI spec \(.json, .yaml, .yml\) up to 5MB/)
      ).toBeInTheDocument();
    });

    it('renders file input with correct accept attribute', () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('accept', '.json,.yaml,.yml');
    });

    it('hides upload zone when file is uploaded', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['{"openapi": "3.0.0"}'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.queryByText(/Click to browse/)).not.toBeInTheDocument();
      });
    });

    it('disables upload zone when isLoading is true', () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} isLoading={true} />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toBeDisabled();
    });
  });

  describe('File selection via input', () => {
    it('calls onFileSelect with valid JSON file', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const fileContent = '{"openapi": "3.0.0"}';
      const file = new File([fileContent], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file, fileContent);
      });
    });

    it('calls onFileSelect with valid YAML file', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const fileContent = 'openapi: 3.0.0\ninfo:\n  title: Test';
      const file = new File([fileContent], 'spec.yaml', {
        type: 'application/yaml',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file, fileContent);
      });
    });

    it('calls onFileSelect with valid YML file', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const fileContent = 'openapi: 3.0.0';
      const file = new File([fileContent], 'spec.yml', {
        type: 'application/yaml',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file, fileContent);
      });
    });
  });

  describe('File validation', () => {
    it('shows error for file exceeding 5MB size limit', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      // Create a 6MB file (exceeds 5MB limit)
      const largeContent = 'x'.repeat(6 * 1024 * 1024);
      const file = new File([largeContent], 'large.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText(/File too large/)).toBeInTheDocument();
        expect(screen.getByText(/Maximum size is 5MB/)).toBeInTheDocument();
      });

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });

    it('shows error for invalid file type', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['content'], 'document.txt', {
        type: 'text/plain',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText(/Invalid file type/)).toBeInTheDocument();
        expect(
          screen.getByText(/Accepted: .json, .yaml, .yml/)
        ).toBeInTheDocument();
      });

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });

    it('accepts uppercase file extensions', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const fileContent = '{"openapi": "3.0.0"}';
      const file = new File([fileContent], 'spec.JSON', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file, fileContent);
      });
    });

    it('shows error when file read fails', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      // Create a mock file that will fail to read
      const file = new File(['content'], 'spec.json', {
        type: 'application/json',
      });

      // Mock the text() method to throw an error
      jest.spyOn(file, 'text').mockRejectedValue(new Error('Read failed'));

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText(/Failed to read file content/)).toBeInTheDocument();
      });

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });
  });

  describe('Drag and drop functionality', () => {
    it('highlights upload zone on drag enter', () => {
      const { container } = render(
        <OpenAPIUpload onFileSelect={mockOnFileSelect} />
      );

      const dropzone = container.querySelector('.border-dashed') as HTMLElement;
      fireEvent.dragEnter(dropzone);

      expect(dropzone).toHaveClass('border-accent-blue');
      expect(dropzone).toHaveClass('bg-accent-blue/5');
    });

    it('removes highlight on drag leave', () => {
      const { container } = render(
        <OpenAPIUpload onFileSelect={mockOnFileSelect} />
      );

      const dropzone = container.querySelector('.border-dashed') as HTMLElement;
      fireEvent.dragEnter(dropzone);
      fireEvent.dragLeave(dropzone);

      expect(dropzone).not.toHaveClass('border-accent-blue');
      expect(dropzone).not.toHaveClass('bg-accent-blue/5');
    });

    it('handles file drop with valid file', async () => {
      const { container } = render(
        <OpenAPIUpload onFileSelect={mockOnFileSelect} />
      );

      const fileContent = '{"openapi": "3.0.0"}';
      const file = new File([fileContent], 'spec.json', {
        type: 'application/json',
      });

      const dropzone = container.querySelector('.border-dashed') as HTMLElement;
      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [file],
        },
      });

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file, fileContent);
      });
    });

    it('prevents default behavior on drag over', () => {
      const { container } = render(
        <OpenAPIUpload onFileSelect={mockOnFileSelect} />
      );

      const dropzone = container.querySelector('.border-dashed') as HTMLElement;
      const dragEvent = new Event('dragover', { bubbles: true, cancelable: true });
      const preventDefaultSpy = jest.spyOn(dragEvent, 'preventDefault');

      dropzone.dispatchEvent(dragEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe('File preview', () => {
    it('displays uploaded file name and size', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const fileContent = '{"openapi": "3.0.0"}';
      const file = new File([fileContent], 'my-api-spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText('my-api-spec.json')).toBeInTheDocument();
        // File size in KB
        const sizeInKB = (file.size / 1024).toFixed(2);
        expect(screen.getByText(`${sizeInKB} KB`)).toBeInTheDocument();
      });
    });

    it('displays file icon in preview', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['content'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        // FileText icon should be rendered (from lucide-react)
        const icon = document.querySelector('svg');
        expect(icon).toBeInTheDocument();
      });
    });

    it('applies error styling when file has error', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      // Upload a file that exceeds size limit
      const largeContent = 'x'.repeat(6 * 1024 * 1024);
      const file = new File([largeContent], 'large.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText('File too large')).toBeInTheDocument();
      });
    });

    it('displays file when valid file is uploaded', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['{"openapi": "3.0.0"}'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText('spec.json')).toBeInTheDocument();
      });
    });
  });

  describe('Remove file functionality', () => {
    it('renders remove button when file is uploaded', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['content'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        const removeButton = screen.getByRole('button');
        expect(removeButton).toBeInTheDocument();
      });
    });

    it('removes file and shows upload zone when remove button is clicked', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['content'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByText('spec.json')).toBeInTheDocument();
      });

      const removeButton = screen.getByRole('button');
      fireEvent.click(removeButton);

      await waitFor(() => {
        expect(screen.queryByText('spec.json')).not.toBeInTheDocument();
        expect(screen.getByText(/Click to browse/)).toBeInTheDocument();
      });
    });

    it('hides remove button when isLoading is true', async () => {
      const { rerender } = render(
        <OpenAPIUpload onFileSelect={mockOnFileSelect} />
      );

      const file = new File(['content'], 'spec.json', {
        type: 'application/json',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByRole('button')).toBeInTheDocument();
      });

      rerender(<OpenAPIUpload onFileSelect={mockOnFileSelect} isLoading={true} />);

      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper label for file input', () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      const label = document.querySelector('label[for="file-upload"]');

      expect(input).toHaveAttribute('id', 'file-upload');
      expect(label).toBeInTheDocument();
    });

    it('uses sr-only class to hide file input visually', () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toHaveClass('sr-only');
    });

    it('displays error icon with error message', async () => {
      render(<OpenAPIUpload onFileSelect={mockOnFileSelect} />);

      const file = new File(['content'], 'document.txt', {
        type: 'text/plain',
      });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      await waitFor(() => {
        // AlertCircle icon should be rendered with error
        const errorSection = screen.getByText(/Invalid file type/).parentElement;
        expect(errorSection).toBeInTheDocument();
        expect(errorSection?.querySelector('svg')).toBeInTheDocument();
      });
    });
  });
});
