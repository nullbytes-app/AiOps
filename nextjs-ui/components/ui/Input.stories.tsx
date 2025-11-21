import type { Meta } from '@storybook/react'
import { Input } from './Input'

/**
 * Input component with glassmorphic design and form features.
 *
 * Features:
 * - Label support
 * - Error state with message
 * - Help text
 * - Multiple input types (text, email, password, number)
 * - Disabled state
 */
const meta = {
  title: 'UI/Input',
  component: Input,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    label: {
      control: 'text',
      description: 'Input label text',
    },
    error: {
      control: 'text',
      description: 'Error message (shows error state)',
    },
    helpText: {
      control: 'text',
      description: 'Help text below input',
    },
    type: {
      control: 'select',
      options: ['text', 'email', 'password', 'number'],
      description: 'HTML input type',
    },
    disabled: {
      control: 'boolean',
      description: 'Disables the input',
    },
    required: {
      control: 'boolean',
      description: 'Makes field required',
    },
    placeholder: {
      control: 'text',
      description: 'Placeholder text',
    },
  },
} satisfies Meta<typeof Input>

export default meta

export const Default = {
  args: {
    placeholder: 'Enter text...',
  },
}

export const WithLabel = {
  args: {
    label: 'Email',
    placeholder: 'Enter your email',
  },
}

export const WithError = {
  args: {
    label: 'Username',
    error: 'This field is required',
    placeholder: 'Enter username',
  },
}

export const WithHelpText = {
  args: {
    label: 'Password',
    helpText: 'Must be at least 8 characters',
    type: 'password',
    placeholder: 'Enter password',
  },
}

export const Email = {
  args: {
    label: 'Email',
    type: 'email',
    placeholder: 'you@example.com',
  },
}

export const Password = {
  args: {
    label: 'Password',
    type: 'password',
    placeholder: 'Enter password',
  },
}

export const Number = {
  args: {
    label: 'Age',
    type: 'number',
    placeholder: '25',
  },
}

export const Disabled = {
  args: {
    label: 'Disabled Input',
    disabled: true,
    placeholder: 'Cannot edit',
    value: 'Disabled value',
  },
}

export const Required = {
  args: {
    label: 'Required Field',
    required: true,
    placeholder: 'This field is required',
  },
}

export const FormExample = {
  render: () => (
    <form className="flex flex-col gap-4 w-96">
      <Input
        label="Email"
        type="email"
        placeholder="you@example.com"
        required
      />
      <Input
        label="Password"
        type="password"
        placeholder="Enter password"
        helpText="Must be at least 8 characters"
        required
      />
      <Input
        label="Username"
        placeholder="Choose a username"
      />
      <Input
        label="Age"
        type="number"
        placeholder="25"
      />
    </form>
  ),
}
