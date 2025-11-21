import type { Meta, StoryObj } from '@storybook/react'
import { Badge } from './Badge'

/**
 * Badge component for status indicators.
 *
 * Features:
 * - 5 variants: default, success, warning, error, info
 * - 2 sizes: sm, md
 * - Inline-flex design for flexible layouts
 */
const meta = {
  title: 'UI/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'success', 'warning', 'error', 'info'],
      description: 'Badge color variant',
    },
    size: {
      control: 'select',
      options: ['sm', 'md'],
      description: 'Badge size',
    },
  },
} satisfies Meta<typeof Badge>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    children: 'Default',
    variant: 'default',
  },
}

export const Success: Story = {
  args: {
    children: 'Success',
    variant: 'success',
  },
}

export const Warning: Story = {
  args: {
    children: 'Warning',
    variant: 'warning',
  },
}

export const Error: Story = {
  args: {
    children: 'Error',
    variant: 'error',
  },
}

export const Info: Story = {
  args: {
    children: 'Info',
    variant: 'info',
  },
}

export const Small: Story = {
  args: {
    children: 'Small',
    size: 'sm',
  },
}

export const Medium: Story = {
  args: {
    children: 'Medium',
    size: 'md',
  },
}

export const WithIcon: Story = {
  args: {
    variant: 'success',
    children: (
      <>
        <span>✓</span>
        <span>Active</span>
      </>
    ),
  },
}

export const AllVariants = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 items-center">
        <span className="text-sm text-gray-600 w-20">Variants:</span>
        <Badge variant="default">Default</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="warning">Warning</Badge>
        <Badge variant="error">Error</Badge>
        <Badge variant="info">Info</Badge>
      </div>
      <div className="flex gap-2 items-center">
        <span className="text-sm text-gray-600 w-20">Sizes:</span>
        <Badge size="sm">Small</Badge>
        <Badge size="md">Medium</Badge>
      </div>
      <div className="flex gap-2 items-center">
        <span className="text-sm text-gray-600 w-20">With icons:</span>
        <Badge variant="success">
          <span>✓</span>
          <span>Active</span>
        </Badge>
        <Badge variant="error">
          <span>✕</span>
          <span>Error</span>
        </Badge>
        <Badge variant="info">
          <span>ℹ</span>
          <span>Info</span>
        </Badge>
      </div>
    </div>
  ),
}

export const StatusExample = {
  render: () => (
    <div className="space-y-3 w-64">
      <div className="flex justify-between items-center">
        <span className="text-sm">Deployment</span>
        <Badge variant="success">Live</Badge>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm">Build</span>
        <Badge variant="warning">In Progress</Badge>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm">Tests</span>
        <Badge variant="error">Failed</Badge>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm">Database</span>
        <Badge variant="info">Migrating</Badge>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm">Cache</span>
        <Badge variant="default">Inactive</Badge>
      </div>
    </div>
  ),
}
