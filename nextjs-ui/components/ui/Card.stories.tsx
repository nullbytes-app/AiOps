import type { Meta } from '@storybook/react'
import { Card } from './Card'

/**
 * Card component with glassmorphic design.
 *
 * Features:
 * - Glassmorphism styling
 * - Configurable padding (none, sm, md, lg)
 * - Optional hover effect
 */
const meta = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    padding: {
      control: 'select',
      options: ['none', 'sm', 'md', 'lg'],
      description: 'Card padding size',
    },
    hover: {
      control: 'boolean',
      description: 'Enable hover transform effect',
    },
    className: {
      control: 'text',
      description: 'Additional CSS classes',
    },
  },
} satisfies Meta<typeof Card>

export default meta

export const Default = {
  args: {
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Card Title</h3>
        <p className="text-sm text-gray-600">
          This is a card with default padding.
        </p>
      </div>
    ),
  },
}

export const NoPadding = {
  args: {
    padding: 'none',
    children: (
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-2">No Padding</h3>
        <p className="text-sm text-gray-600">
          Card with no padding (padding managed by children).
        </p>
      </div>
    ),
  },
}

export const SmallPadding = {
  args: {
    padding: 'sm',
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Small Padding</h3>
        <p className="text-sm text-gray-600">
          Card with small padding (p-3).
        </p>
      </div>
    ),
  },
}

export const LargePadding = {
  args: {
    padding: 'lg',
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Large Padding</h3>
        <p className="text-sm text-gray-600">
          Card with large padding (p-8).
        </p>
      </div>
    ),
  },
}

export const WithHover = {
  args: {
    hover: true,
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Hover Me!</h3>
        <p className="text-sm text-gray-600">
          This card scales slightly on hover.
        </p>
      </div>
    ),
  },
}

export const WithoutHover = {
  args: {
    hover: false,
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">No Hover Effect</h3>
        <p className="text-sm text-gray-600">
          This card has no hover effect.
        </p>
      </div>
    ),
  },
}

export const ComplexContent = {
  args: {
    children: (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">User Profile</h3>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
            Active
          </span>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Name:</span>
            <span className="font-medium">John Doe</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Role:</span>
            <span className="font-medium">Admin</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Joined:</span>
            <span className="font-medium">Jan 2024</span>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button className="w-full py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
            View Details
          </button>
        </div>
      </div>
    ),
  },
}

export const GridLayout = {
  render: () => (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <h4 className="font-semibold mb-2">Card 1</h4>
        <p className="text-sm text-gray-600">Content here</p>
      </Card>
      <Card>
        <h4 className="font-semibold mb-2">Card 2</h4>
        <p className="text-sm text-gray-600">Content here</p>
      </Card>
      <Card>
        <h4 className="font-semibold mb-2">Card 3</h4>
        <p className="text-sm text-gray-600">Content here</p>
      </Card>
    </div>
  ),
}
