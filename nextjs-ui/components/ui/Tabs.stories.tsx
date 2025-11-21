import type { Meta } from '@storybook/react';
import { Tabs } from './Tabs';
import { Home, Settings, User, Bell, Mail, Calendar, FileText, Image, Music } from 'lucide-react';
import { useState } from 'react';

const meta: Meta<typeof Tabs> = {
  title: 'UI/Tabs',
  component: Tabs,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;

const simpleTabs = [
  {
    key: 'overview',
    label: 'Overview',
    content: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Overview</h3>
        <p className="text-gray-600 dark:text-gray-400">
          This is the overview tab. It contains general information about the content.
        </p>
      </div>
    ),
  },
  {
    key: 'details',
    label: 'Details',
    content: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Details</h3>
        <p className="text-gray-600 dark:text-gray-400">
          Detailed information and specifications are displayed here.
        </p>
      </div>
    ),
  },
  {
    key: 'settings',
    label: 'Settings',
    content: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Settings</h3>
        <p className="text-gray-600 dark:text-gray-400">
          Configure your preferences and settings in this section.
        </p>
      </div>
    ),
  },
];

export const Default = {
  args: {
    tabs: simpleTabs,
    variant: 'pills',
  },
};

export const WithIcons = {
  args: {
    tabs: [
      {
        key: 'home',
        label: 'Home',
        icon: <Home size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Home Dashboard</h3>
            <p className="text-gray-600 dark:text-gray-400">
              Welcome to your home dashboard. Here you can see an overview of your recent activity.
            </p>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">24</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Active Projects</div>
              </div>
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">12</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Completed Tasks</div>
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'profile',
        label: 'Profile',
        icon: <User size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">User Profile</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">Name:</span>
                <span className="text-gray-600 dark:text-gray-400">John Doe</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">Email:</span>
                <span className="text-gray-600 dark:text-gray-400">john.doe@example.com</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">Role:</span>
                <span className="text-gray-600 dark:text-gray-400">Administrator</span>
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'notifications',
        label: 'Notifications',
        icon: <Bell size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Notifications</h3>
            <div className="space-y-2">
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div className="font-medium">New message received</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">2 minutes ago</div>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div className="font-medium">Task completed</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">1 hour ago</div>
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'settings',
        label: 'Settings',
        icon: <Settings size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Settings</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                <span>Enable notifications</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                <span>Dark mode</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                <span>Auto-save</span>
              </label>
            </div>
          </div>
        ),
      },
    ],
    variant: 'pills',
  },
};

export const PillsVariant = {
  args: {
    tabs: simpleTabs,
    variant: 'pills',
  },
};

export const UnderlineVariant = {
  args: {
    tabs: simpleTabs,
    variant: 'underline',
  },
};

export const BoxedVariant = {
  args: {
    tabs: simpleTabs,
    variant: 'boxed',
  },
};

export const FullWidth = {
  args: {
    tabs: simpleTabs,
    variant: 'pills',
    fullWidth: true,
  },
};

export const WithDisabledTab = {
  args: {
    tabs: [
      {
        key: 'active1',
        label: 'Active Tab 1',
        content: <div>This tab is active and clickable.</div>,
      },
      {
        key: 'disabled',
        label: 'Disabled Tab',
        content: <div>This content should not be visible.</div>,
        disabled: true,
      },
      {
        key: 'active2',
        label: 'Active Tab 2',
        content: <div>Another active tab.</div>,
      },
    ],
    variant: 'pills',
  },
};

export const DefaultIndex = {
  args: {
    tabs: simpleTabs,
    variant: 'pills',
    defaultIndex: 1,
  },
};

export const Controlled = {
  render: () => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    return (
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedIndex(0)}
            className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Go to Tab 1
          </button>
          <button
            onClick={() => setSelectedIndex(1)}
            className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Go to Tab 2
          </button>
          <button
            onClick={() => setSelectedIndex(2)}
            className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Go to Tab 3
          </button>
        </div>
        <Tabs
          tabs={simpleTabs}
          selectedIndex={selectedIndex}
          onChange={setSelectedIndex}
          variant="pills"
        />
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Current tab index: {selectedIndex}
        </div>
      </div>
    );
  },
};

export const WithOnChange = {
  render: () => {
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [history, setHistory] = useState<number[]>([0]);

    const handleChange = (index: number) => {
      setSelectedIndex(index);
      setHistory((prev) => [...prev, index]);
    };

    return (
      <div className="space-y-4">
        <Tabs tabs={simpleTabs} selectedIndex={selectedIndex} onChange={handleChange} variant="pills" />
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-sm font-medium mb-2">Tab Change History:</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {history.map((idx, i) => (
              <span key={i}>
                {idx}
                {i < history.length - 1 && ' → '}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  },
};

export const ManyTabs = {
  args: {
    tabs: [
      { key: '1', label: 'Tab 1', content: <div>Content 1</div> },
      { key: '2', label: 'Tab 2', content: <div>Content 2</div> },
      { key: '3', label: 'Tab 3', content: <div>Content 3</div> },
      { key: '4', label: 'Tab 4', content: <div>Content 4</div> },
      { key: '5', label: 'Tab 5', content: <div>Content 5</div> },
      { key: '6', label: 'Tab 6', content: <div>Content 6</div> },
      { key: '7', label: 'Tab 7', content: <div>Content 7</div> },
      { key: '8', label: 'Tab 8', content: <div>Content 8</div> },
    ],
    variant: 'pills',
  },
};

export const MediaLibrary = {
  args: {
    tabs: [
      {
        key: 'images',
        label: 'Images',
        // eslint-disable-next-line jsx-a11y/alt-text
        icon: <Image size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Image Gallery</h3>
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-lg" />
              ))}
            </div>
          </div>
        ),
      },
      {
        key: 'music',
        label: 'Music',
        icon: <Music size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Music Library</h3>
            <div className="space-y-2">
              {['Song 1', 'Song 2', 'Song 3', 'Song 4'].map((song) => (
                <div key={song} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-center gap-3">
                  <Music size={16} className="text-gray-400" />
                  <span>{song}</span>
                </div>
              ))}
            </div>
          </div>
        ),
      },
      {
        key: 'documents',
        label: 'Documents',
        icon: <FileText size={16} />,
        content: (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Documents</h3>
            <div className="space-y-2">
              {['Report.pdf', 'Presentation.pptx', 'Spreadsheet.xlsx'].map((doc) => (
                <div key={doc} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-center gap-3">
                  <FileText size={16} className="text-gray-400" />
                  <span>{doc}</span>
                </div>
              ))}
            </div>
          </div>
        ),
      },
    ],
    variant: 'underline',
  },
};

export const ContactMethods = {
  args: {
    tabs: [
      {
        key: 'email',
        label: 'Email',
        icon: <Mail size={16} />,
        content: (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Contact via Email</h3>
            <form className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Your Email</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Message</label>
                <textarea
                  rows={4}
                  placeholder="Your message..."
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                />
              </div>
              <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                Send Email
              </button>
            </form>
          </div>
        ),
      },
      {
        key: 'calendar',
        label: 'Schedule',
        icon: <Calendar size={16} />,
        content: (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Schedule a Meeting</h3>
            <form className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Date</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Time</label>
                <input
                  type="time"
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                />
              </div>
              <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                Book Meeting
              </button>
            </form>
          </div>
        ),
      },
    ],
    variant: 'boxed',
  },
};

export const Showcase = {
  render: () => {
    const [variant, setVariant] = useState<'pills' | 'underline' | 'boxed'>('pills');
    const [fullWidth, setFullWidth] = useState(false);

    return (
      <div className="space-y-6">
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Tabs Showcase</h3>
          <div className="flex flex-wrap gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Variant</label>
              <div className="flex gap-2">
                {(['pills', 'underline', 'boxed'] as const).map((v) => (
                  <button
                    key={v}
                    onClick={() => setVariant(v)}
                    className={`px-3 py-1.5 text-sm rounded ${
                      variant === v
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                    }`}
                  >
                    {v.charAt(0).toUpperCase() + v.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Layout</label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={fullWidth}
                  onChange={(e) => setFullWidth(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Full Width</span>
              </label>
            </div>
          </div>
        </div>
        <Tabs
          tabs={[
            {
              key: 'home',
              label: 'Home',
              icon: <Home size={16} />,
              content: (
                <div>
                  <h4 className="font-semibold mb-2">Home Tab</h4>
                  <p className="text-gray-600 dark:text-gray-400">This is the home tab content.</p>
                </div>
              ),
            },
            {
              key: 'profile',
              label: 'Profile',
              icon: <User size={16} />,
              content: (
                <div>
                  <h4 className="font-semibold mb-2">Profile Tab</h4>
                  <p className="text-gray-600 dark:text-gray-400">User profile information goes here.</p>
                </div>
              ),
            },
            {
              key: 'settings',
              label: 'Settings',
              icon: <Settings size={16} />,
              content: (
                <div>
                  <h4 className="font-semibold mb-2">Settings Tab</h4>
                  <p className="text-gray-600 dark:text-gray-400">Configure your preferences here.</p>
                </div>
              ),
            },
          ]}
          variant={variant}
          fullWidth={fullWidth}
        />
      </div>
    );
  },
};
