import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button, Card, Field, Meter } from '../components/ui'

describe('Button', () => {
  it('handles clicks and respects disabled', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    const { rerender } = render(<Button onClick={onClick}>Go</Button>)
    await user.click(screen.getByRole('button', { name: 'Go' }))
    expect(onClick).toHaveBeenCalledTimes(1)

    rerender(
      <Button onClick={onClick} disabled>
        Go
      </Button>,
    )
    await user.click(screen.getByRole('button', { name: 'Go' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})

describe('Field', () => {
  it('associates the label and hint with the input', () => {
    render(<Field label="Exam date" hint="When you sit the test" />)
    const input = screen.getByLabelText('Exam date')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAccessibleDescription('When you sit the test')
  })
})

describe('Card', () => {
  it('renders its children', () => {
    render(<Card>Inside</Card>)
    expect(screen.getByText('Inside')).toBeInTheDocument()
  })
})

describe('Meter', () => {
  it('exposes an accessible meter role with a clamped value', () => {
    render(<Meter value={150} max={100} label="Reading" />)
    const meter = screen.getByRole('meter', { name: 'Reading' })
    expect(meter).toHaveAttribute('aria-valuenow', '100')
    expect(meter).toHaveAttribute('aria-valuemax', '100')
  })
})
