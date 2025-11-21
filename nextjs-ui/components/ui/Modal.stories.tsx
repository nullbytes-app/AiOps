import type { Meta } from '@storybook/react';
import { Modal, ModalProps } from './Modal';
import { useState } from 'react';

const meta: Meta<typeof Modal> = {
  title: 'UI/Modal',
  component: Modal,
  tags: ['autodocs'],
  argTypes: {
    isOpen: { control: 'boolean' },
    size: { control: { type: 'select' }, options: ['sm', 'md', 'lg', 'xl'] },
    preventBackdropClose: { control: 'boolean' },
    showCloseButton: { control: 'boolean' },
  },
};

export default meta;

// Wrapper component to handle modal state
const ModalWrapper = ({ children, ...args }: Partial<ModalProps>) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div>
      <button
        onClick={() => setIsOpen(true)}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
      >
        Open Modal
      </button>
      <Modal {...args} isOpen={isOpen} onClose={() => setIsOpen(false)}>
        {children}
      </Modal>
    </div>
  );
};

export const Default = {
  render: () => (
    <ModalWrapper>
      <p>This is the default modal content. Click outside or press Escape to close.</p>
    </ModalWrapper>
  ),
};

export const WithTitle = {
  render: () => (
    <ModalWrapper title="Welcome">
      <p>This modal has a title. The title is announced to screen readers via aria-labelledby.</p>
    </ModalWrapper>
  ),
};

export const WithTitleAndDescription = {
  render: () => (
    <ModalWrapper title="Delete Account" description="This action cannot be undone.">
      <p>Are you sure you want to permanently delete your account? All your data will be lost.</p>
    </ModalWrapper>
  ),
};

export const WithFooter = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <div>
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg"
        >
          Open Modal with Footer
        </button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Confirm Action"
          description="Please review before proceeding."
          footer={
            <>
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert('Action confirmed!');
                  setIsOpen(false);
                }}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Delete
              </button>
            </>
          }
        >
          <p>This action will permanently delete the selected item.</p>
        </Modal>
      </div>
    );
  },
};

export const Small = {
  render: () => (
    <ModalWrapper title="Small Modal" size="sm">
      <p>This is a small modal (max-width: 384px).</p>
    </ModalWrapper>
  ),
};

export const Medium = {
  render: () => (
    <ModalWrapper title="Medium Modal" size="md">
      <p>This is a medium modal (max-width: 512px). This is the default size.</p>
    </ModalWrapper>
  ),
};

export const Large = {
  render: () => (
    <ModalWrapper title="Large Modal" size="lg">
      <p>This is a large modal (max-width: 768px). Useful for forms or detailed content.</p>
      <div className="mt-4 space-y-2">
        <input type="text" placeholder="Name" className="w-full px-3 py-2 border rounded" />
        <input type="email" placeholder="Email" className="w-full px-3 py-2 border rounded" />
        <textarea placeholder="Message" className="w-full px-3 py-2 border rounded" rows={4} />
      </div>
    </ModalWrapper>
  ),
};

export const ExtraLarge = {
  render: () => (
    <ModalWrapper title="Extra Large Modal" size="xl">
      <p>This is an extra-large modal (max-width: 1024px). Good for complex layouts.</p>
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="p-4 bg-gray-100 rounded">Column 1</div>
        <div className="p-4 bg-gray-100 rounded">Column 2</div>
      </div>
    </ModalWrapper>
  ),
};

export const PreventBackdropClose = {
  render: () => (
    <ModalWrapper
      title="Important Notice"
      description="You must take action before closing this modal."
      preventBackdropClose={true}
    >
      <p>This modal cannot be closed by clicking the backdrop or pressing Escape.</p>
      <p className="mt-2 text-sm text-gray-600">
        Only the close button or footer actions can close this modal.
      </p>
    </ModalWrapper>
  ),
};

export const NoCloseButton = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <div>
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg"
        >
          Open Modal
        </button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="No Close Button"
          showCloseButton={false}
          footer={
            <button
              onClick={() => setIsOpen(false)}
              className="px-4 py-2 bg-gray-200 rounded-lg"
            >
              Close
            </button>
          }
        >
          <p>This modal has no close button in the header. Use the footer button to close.</p>
        </Modal>
      </div>
    );
  },
};

export const LongContent = {
  render: () => (
    <ModalWrapper title="Long Content Modal" size="lg">
      <p>This modal has long scrollable content:</p>
      <div className="mt-4 space-y-4">
        {Array.from({ length: 20 }, (_, i) => (
          <p key={i} className="text-sm">
            Paragraph {i + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do
            eiusmod tempor incididunt ut labore et dolore magna aliqua.
          </p>
        ))}
      </div>
    </ModalWrapper>
  ),
};

export const FormExample = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      alert('Form submitted!');
      setIsOpen(false);
    };

    return (
      <div>
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg"
        >
          Create New Item
        </button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Create Item"
          description="Fill in the details below."
          size="lg"
          footer={
            <form onSubmit={handleSubmit} className="contents">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Create
              </button>
            </form>
          }
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" className="w-full px-3 py-2 border rounded-lg" required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea className="w-full px-3 py-2 border rounded-lg" rows={4} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select className="w-full px-3 py-2 border rounded-lg">
                <option>General</option>
                <option>Important</option>
                <option>Urgent</option>
              </select>
            </div>
          </form>
        </Modal>
      </div>
    );
  },
};

export const CustomStyling = {
  render: () => (
    <ModalWrapper
      title="Custom Styled Modal"
      className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20"
    >
      <p>This modal has custom gradient background styling applied via className prop.</p>
      <div className="mt-4 p-4 bg-white/50 dark:bg-black/50 rounded-lg">
        <p className="text-sm">Custom content area with semi-transparent background.</p>
      </div>
    </ModalWrapper>
  ),
};

export const Showcase = {
  render: () => {
    const [activeModal, setActiveModal] = useState<string | null>(null);

    const modals = [
      { id: 'info', title: 'Information', size: 'sm' as const, variant: 'Info' },
      { id: 'warning', title: 'Warning', size: 'md' as const, variant: 'Warning' },
      { id: 'error', title: 'Error', size: 'md' as const, variant: 'Error' },
      { id: 'form', title: 'Form', size: 'lg' as const, variant: 'Form' },
    ];

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Modal Showcase</h3>
        <div className="grid grid-cols-2 gap-4">
          {modals.map((modal) => (
            <button
              key={modal.id}
              onClick={() => setActiveModal(modal.id)}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg"
            >
              {modal.variant}
            </button>
          ))}
        </div>

        <Modal
          isOpen={activeModal === 'info'}
          onClose={() => setActiveModal(null)}
          title="Information"
          description="Helpful information for the user."
          size="sm"
          footer={
            <button
              onClick={() => setActiveModal(null)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg"
            >
              Got it
            </button>
          }
        >
          <p>This is an informational modal with helpful details.</p>
        </Modal>

        <Modal
          isOpen={activeModal === 'warning'}
          onClose={() => setActiveModal(null)}
          title="Warning"
          description="Please review this warning carefully."
          footer={
            <>
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 bg-yellow-500 text-white rounded-lg"
              >
                Proceed with Caution
              </button>
            </>
          }
        >
          <p>This action may have unintended consequences. Are you sure you want to continue?</p>
        </Modal>

        <Modal
          isOpen={activeModal === 'error'}
          onClose={() => setActiveModal(null)}
          title="Error Occurred"
          description="An error has been detected."
          footer={
            <button
              onClick={() => setActiveModal(null)}
              className="px-4 py-2 bg-red-500 text-white rounded-lg"
            >
              Close
            </button>
          }
        >
          <p>The operation failed due to an unexpected error. Please try again later.</p>
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
            <p className="text-sm font-mono text-red-700 dark:text-red-300">
              Error code: ERR_NETWORK_TIMEOUT
            </p>
          </div>
        </Modal>

        <Modal
          isOpen={activeModal === 'form'}
          onClose={() => setActiveModal(null)}
          title="Edit Profile"
          description="Update your profile information."
          size="lg"
          footer={
            <>
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 bg-green-500 text-white rounded-lg"
              >
                Save Changes
              </button>
            </>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Full Name</label>
              <input
                type="text"
                defaultValue="John Doe"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                defaultValue="john@example.com"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
        </Modal>
      </div>
    );
  },
};
