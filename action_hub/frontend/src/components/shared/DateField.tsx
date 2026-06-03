import { Form, InputGroup } from 'react-bootstrap'

interface DateFieldProps {
  name: string
  label?: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  disabled?: boolean
  minDate?: string
  maxDate?: string
  helpText?: string
}

export default function DateField({
  name,
  label,
  value,
  onChange,
  required = false,
  disabled = false,
  minDate,
  maxDate,
  helpText,
}: DateFieldProps) {
  // Format date for display based on locale
  const formatDateForInput = (dateValue: string) => {
    if (!dateValue) return ''
    try {
      const date = new Date(dateValue)
      return date.toISOString().split('T')[0]
    } catch {
      return dateValue
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
  }

  return (
    <Form.Group className="mb-3">
      {label && <Form.Label>{label}{required && ' *'}</Form.Label>}
      <InputGroup>
        <Form.Control
          type="date"
          name={name}
          value={formatDateForInput(value)}
          onChange={handleChange}
          required={required}
          disabled={disabled}
          min={minDate}
          max={maxDate}
        />
      </InputGroup>
      {helpText && <Form.Text className="text-muted">{helpText}</Form.Text>}
    </Form.Group>
  )
}