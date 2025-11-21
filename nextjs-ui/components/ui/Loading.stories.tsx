import type { Meta } from '@storybook/react'
import { Loading } from './Loading'

/**
 * Loading spinner component.
 *
 * Features:
 * - Animated spinning circle
 * - 3 sizes: sm, md, lg
 * - Optional loading text
 * - Uses accent-blue color
 */
const meta = {
  title: 'UI/Loading',
  component: Loading,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
      description: 'Spinner size',
    },
    text: {
      control: 'text',
      description: 'Optional loading text',
    },
  },
} satisfies Meta<typeof Loading>

export default meta

export const Default = {
  args: {},
}

export const Small = {
  args: {
    size: 'sm',
  },
}

export const Medium = {
  args: {
    size: 'md',
  },
}

export const Large = {
  args: {
    size: 'lg',
  },
}

export const WithText = {
  args: {
    text: 'Loading...',
  },
}

export const SmallWithText = {
  args: {
    size: 'sm',
    text: 'Loading...',
  },
}

export const LargeWithText = {
  args: {
    size: 'lg',
    text: 'Please wait...',
  },
}

export const CustomText = {
  args: {
    text: 'Fetching data...',
  },
}

export const AllSizes = {
  render: () => (
    <div className="flex gap-8 items-start">
      <div className="flex flex-col items-center gap-2">
        <span className="text-sm text-gray-600 mb-2">Small</span>
        <Loading size="sm" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <span className="text-sm text-gray-600 mb-2">Medium</span>
        <Loading size="md" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <span className="text-sm text-gray-600 mb-2">Large</span>
        <Loading size="lg" />
      </div>
    </div>
  ),
}

export const InlineExample = {
  render: () => (
    <div className="flex items-center gap-2">
      <span>Loading data</span>
      <Loading size="sm" />
    </div>
  ),
}

export const CenteredExample = {
  render: () => (
    <div className="w-96 h-64 flex items-center justify-center bg-gray-50 rounded-lg">
      <Loading text="Loading content..." />
    </div>
  ),
}

export const FullScreenExample = {
  render: () => (
    <div className="fixed inset-0 flex items-center justify-center bg-white bg-opacity-90">
      <Loading size="lg" text="Loading application..." />
    </div>
  ),
  parameters: {
    layout: 'fullscreen',
  },
}
