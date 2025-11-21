import type { Meta } from '@storybook/react';
import { Tooltip } from './Tooltip';
import { Info, HelpCircle, Settings, AlertCircle, CheckCircle, X } from 'lucide-react';

const meta: Meta<typeof Tooltip> = {
  title: 'UI/Tooltip',
  component: Tooltip,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
  argTypes: {
    placement: {
      control: 'select',
      options: ['top', 'bottom', 'left', 'right'],
    },
    delay: {
      control: { type: 'number', min: 0, max: 2000, step: 100 },
    },
    disabled: {
      control: 'boolean',
    },
  },
};

export default meta;

export const Default = {
  args: {
    content: 'This is a tooltip',
    placement: 'top',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Hover me</button>,
  },
};

export const TopPlacement = {
  args: {
    content: 'Tooltip on top',
    placement: 'top',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Top</button>,
  },
};

export const BottomPlacement = {
  args: {
    content: 'Tooltip on bottom',
    placement: 'bottom',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Bottom</button>,
  },
};

export const LeftPlacement = {
  args: {
    content: 'Tooltip on left',
    placement: 'left',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Left</button>,
  },
};

export const RightPlacement = {
  args: {
    content: 'Tooltip on right',
    placement: 'right',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Right</button>,
  },
};

export const WithIcon = {
  args: {
    content: 'Click for more information',
    placement: 'top',
    children: (
      <button className="p-2 text-blue-500 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-colors">
        <Info size={20} />
      </button>
    ),
  },
};

export const HelpIcon = {
  args: {
    content: 'Need help? Click here to access support documentation and tutorials.',
    placement: 'top',
    children: (
      <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors">
        <HelpCircle size={20} />
      </button>
    ),
  },
};

export const CustomDelay = {
  args: {
    content: 'This tooltip has a 1 second delay',
    placement: 'top',
    delay: 1000,
    children: <button className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600">Slow hover (1s)</button>,
  },
};

export const NoDelay = {
  args: {
    content: 'Instant tooltip!',
    placement: 'top',
    delay: 0,
    children: <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">Instant hover</button>,
  },
};

export const Disabled = {
  args: {
    content: 'You should not see this',
    placement: 'top',
    disabled: true,
    children: <button className="px-4 py-2 bg-gray-400 text-white rounded-lg cursor-not-allowed">Disabled tooltip</button>,
  },
};

export const LongContent = {
  args: {
    content: 'This is a longer tooltip text that demonstrates how the tooltip handles extended content. It wraps nicely and remains readable.',
    placement: 'top',
    children: <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Long text</button>,
  },
};

export const ReactNodeContent = {
  args: {
    content: (
      <div className="flex items-center gap-2">
        <CheckCircle size={16} className="text-green-400" />
        <span>Action completed successfully!</span>
      </div>
    ),
    placement: 'top',
    children: <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">Success</button>,
  },
};

export const ErrorTooltip = {
  args: {
    content: (
      <div className="flex items-center gap-2">
        <AlertCircle size={16} className="text-red-400" />
        <span>Error: Invalid input</span>
      </div>
    ),
    placement: 'top',
    children: (
      <button className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 flex items-center gap-2">
        <X size={16} />
        Error
      </button>
    ),
  },
};

export const OnFormField = {
  render: () => (
    <div className="space-y-4 w-80">
      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Email address
          <Tooltip content="We'll never share your email with anyone else" placement="right" delay={0}>
            <Info size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </label>
        <input
          type="email"
          placeholder="you@example.com"
          className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Password
          <Tooltip content="Password must be at least 8 characters long and include uppercase, lowercase, and numbers" placement="right" delay={0}>
            <HelpCircle size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </label>
        <input
          type="password"
          placeholder="••••••••"
          className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
        />
      </div>
    </div>
  ),
};

export const AllPlacements = {
  render: () => (
    <div className="flex flex-col items-center gap-8">
      <div className="flex items-center gap-8">
        <Tooltip content="Top tooltip" placement="top">
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Top</button>
        </Tooltip>
      </div>

      <div className="flex items-center gap-8">
        <Tooltip content="Left tooltip" placement="left">
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Left</button>
        </Tooltip>

        <div className="w-32" />

        <Tooltip content="Right tooltip" placement="right">
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Right</button>
        </Tooltip>
      </div>

      <div className="flex items-center gap-8">
        <Tooltip content="Bottom tooltip" placement="bottom">
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Bottom</button>
        </Tooltip>
      </div>
    </div>
  ),
};

export const IconButtons = {
  render: () => (
    <div className="flex gap-4">
      <Tooltip content="Information" placement="top">
        <button className="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-colors">
          <Info size={20} />
        </button>
      </Tooltip>

      <Tooltip content="Help & Support" placement="top">
        <button className="p-2 text-purple-500 hover:bg-purple-50 rounded-lg transition-colors">
          <HelpCircle size={20} />
        </button>
      </Tooltip>

      <Tooltip content="Settings" placement="top">
        <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors">
          <Settings size={20} />
        </button>
      </Tooltip>

      <Tooltip content="Warning" placement="top">
        <button className="p-2 text-yellow-500 hover:bg-yellow-50 rounded-lg transition-colors">
          <AlertCircle size={20} />
        </button>
      </Tooltip>

      <Tooltip content="Success" placement="top">
        <button className="p-2 text-green-500 hover:bg-green-50 rounded-lg transition-colors">
          <CheckCircle size={20} />
        </button>
      </Tooltip>
    </div>
  ),
};

export const DataTable = {
  render: () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <div className="flex items-center gap-2">
                Name
                <Tooltip content="User's full name" placement="top" delay={0}>
                  <Info size={14} className="text-gray-400 cursor-help" />
                </Tooltip>
              </div>
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <div className="flex items-center gap-2">
                Email
                <Tooltip content="Primary email address" placement="top" delay={0}>
                  <Info size={14} className="text-gray-400 cursor-help" />
                </Tooltip>
              </div>
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <div className="flex items-center gap-2">
                Status
                <Tooltip content="Account status: Active, Pending, or Inactive" placement="top" delay={0}>
                  <Info size={14} className="text-gray-400 cursor-help" />
                </Tooltip>
              </div>
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          <tr>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">John Doe</td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">john@example.com</td>
            <td className="px-6 py-4 whitespace-nowrap">
              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                Active
              </span>
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">Jane Smith</td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">jane@example.com</td>
            <td className="px-6 py-4 whitespace-nowrap">
              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                Pending
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  ),
};

export const Dashboard = {
  render: () => (
    <div className="grid grid-cols-2 gap-4">
      <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Users</h3>
          <Tooltip content="Total number of registered users" placement="top" delay={0}>
            <Info size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <div className="text-2xl font-bold">1,234</div>
      </div>

      <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Sessions</h3>
          <Tooltip content="Number of currently active user sessions" placement="top" delay={0}>
            <Info size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <div className="text-2xl font-bold">567</div>
      </div>

      <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Conversion Rate</h3>
          <Tooltip content="Percentage of visitors who completed a purchase" placement="top" delay={0}>
            <Info size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <div className="text-2xl font-bold">23.5%</div>
      </div>

      <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Revenue</h3>
          <Tooltip content="Total revenue generated this month" placement="top" delay={0}>
            <Info size={16} className="text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <div className="text-2xl font-bold">$45,678</div>
      </div>
    </div>
  ),
};

export const Showcase = {
  render: () => {
    return (
      <div className="space-y-8 max-w-2xl">
        <div>
          <h3 className="text-lg font-semibold mb-4">Tooltip Showcase</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Hover over buttons and icons to see tooltips in action
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <h4 className="text-sm font-medium mb-3">Placements</h4>
            <div className="flex flex-wrap gap-3">
              <Tooltip content="Top tooltip" placement="top">
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Top</button>
              </Tooltip>
              <Tooltip content="Bottom tooltip" placement="bottom">
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Bottom</button>
              </Tooltip>
              <Tooltip content="Left tooltip" placement="left">
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Left</button>
              </Tooltip>
              <Tooltip content="Right tooltip" placement="right">
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Right</button>
              </Tooltip>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-3">Delays</h4>
            <div className="flex flex-wrap gap-3">
              <Tooltip content="Instant (0ms)" placement="top" delay={0}>
                <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">0ms</button>
              </Tooltip>
              <Tooltip content="Default (200ms)" placement="top" delay={200}>
                <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">200ms</button>
              </Tooltip>
              <Tooltip content="Slow (1000ms)" placement="top" delay={1000}>
                <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">1000ms</button>
              </Tooltip>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-3">Icon Buttons</h4>
            <div className="flex flex-wrap gap-3">
              <Tooltip content="Information" placement="top">
                <button className="p-2 text-blue-500 hover:bg-blue-50 rounded-lg">
                  <Info size={20} />
                </button>
              </Tooltip>
              <Tooltip content="Help" placement="top">
                <button className="p-2 text-purple-500 hover:bg-purple-50 rounded-lg">
                  <HelpCircle size={20} />
                </button>
              </Tooltip>
              <Tooltip content="Settings" placement="top">
                <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
                  <Settings size={20} />
                </button>
              </Tooltip>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-3">States</h4>
            <div className="flex flex-wrap gap-3">
              <Tooltip content="Enabled tooltip" placement="top">
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Enabled</button>
              </Tooltip>
              <Tooltip content="You won't see this" placement="top" disabled>
                <button className="px-4 py-2 bg-gray-400 text-white rounded-lg cursor-not-allowed">Disabled</button>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    );
  },
};
