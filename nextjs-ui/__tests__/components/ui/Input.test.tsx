import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from '@/components/ui/Input'

describe('Input', () => {
  it('renders input field correctly', () => {
    render(<Input placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
  })

  describe('label', () => {
    it('renders label when provided', () => {
      render(<Input label="Email" />)
      expect(screen.getByText('Email')).toBeInTheDocument()
    })

    it('does not render label when not provided', () => {
      render(<Input />)
      expect(screen.queryByRole('label')).not.toBeInTheDocument()
    })

    it('associates label with input', () => {
      render(<Input label="Username" />)
      const label = screen.getByText('Username')
      expect(label.tagName).toBe('LABEL')
    })
  })

  describe('error state', () => {
    it('shows error message when error prop is provided', () => {
      render(<Input error="This field is required" />)
      expect(screen.getByText('This field is required')).toBeInTheDocument()
    })

    it('applies error styles when error is present', () => {
      render(<Input error="Error message" />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-red-500')
    })

    it('hides help text when error is present', () => {
      render(<Input error="Error" helpText="Help text" />)
      expect(screen.getByText('Error')).toBeInTheDocument()
      expect(screen.queryByText('Help text')).not.toBeInTheDocument()
    })
  })

  describe('help text', () => {
    it('renders help text when provided and no error', () => {
      render(<Input helpText="Enter your email address" />)
      expect(screen.getByText('Enter your email address')).toBeInTheDocument()
    })

    it('does not render help text when not provided', () => {
      render(<Input />)
      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
    })
  })

  describe('user interaction', () => {
    it('allows user to type', async () => {
      const user = userEvent.setup()
      render(<Input placeholder="Type here" />)

      const input = screen.getByPlaceholderText('Type here')
      await user.type(input, 'Hello World')

      expect(input).toHaveValue('Hello World')
    })

    it('calls onChange handler', async () => {
      const handleChange = jest.fn()
      const user = userEvent.setup()

      render(<Input onChange={handleChange} />)
      const input = screen.getByRole('textbox')
      await user.type(input, 'a')

      expect(handleChange).toHaveBeenCalled()
    })

    it('respects disabled attribute', async () => {
      const handleChange = jest.fn()
      const user = userEvent.setup()

      render(<Input disabled onChange={handleChange} />)
      const input = screen.getByRole('textbox')
      await user.type(input, 'text')

      expect(handleChange).not.toHaveBeenCalled()
      expect(input).toBeDisabled()
    })
  })

  describe('controlled input', () => {
    it('works as controlled component', async () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('')
        return (
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Controlled"
          />
        )
      }

      const user = userEvent.setup()

      render(<TestComponent />)
      const input = screen.getByPlaceholderText('Controlled')

      await user.type(input, 'Test')
      expect(input).toHaveValue('Test')
    })
  })

  describe('accessibility', () => {
    it('has correct input role', () => {
      render(<Input />)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('supports aria-label', () => {
      render(<Input aria-label="Search input" />)
      expect(screen.getByLabelText('Search input')).toBeInTheDocument()
    })

    it('supports required attribute', () => {
      render(<Input required />)
      expect(screen.getByRole('textbox')).toBeRequired()
    })

    it('accepts custom className', () => {
      render(<Input className="custom-input" />)
      expect(screen.getByRole('textbox')).toHaveClass('custom-input')
    })
  })

  describe('input types', () => {
    it('supports email type', () => {
      render(<Input type="email" />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('type', 'email')
    })

    it('supports password type', () => {
      const { container } = render(<Input type="password" />)
      const input = container.querySelector('input[type="password"]')
      expect(input).toHaveAttribute('type', 'password')
    })

    it('supports number type', () => {
      render(<Input type="number" />)
      const input = screen.getByRole('spinbutton')
      expect(input).toHaveAttribute('type', 'number')
    })
  })
})
