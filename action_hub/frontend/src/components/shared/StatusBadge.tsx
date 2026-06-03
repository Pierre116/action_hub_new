import { Badge } from 'react-bootstrap'

interface StatusBadgeProps {
  status: string
}

const statusColors: Record<string, string> = {
  'Not started': 'primary',
  'On-track': 'info',
  'Late': 'warning',
  'Cancelled': 'danger',
  'Open': 'primary',
  'In Progress': 'info',
  'Under Review': 'warning',
  'On Hold': 'secondary',
  'Done': 'success',
  'Postponed': 'secondary',
}

const legacyStatusLabels: Record<string, string> = {
  'Open': 'Not started',
  'In Progress': 'On-track',
  'Under Review': 'Late',
  'On Hold': 'Late',
  'Postponed': 'On Hold',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalizedStatus = legacyStatusLabels[status] || status
  const variant = statusColors[normalizedStatus] || statusColors[status] || 'secondary'

  return (
    <Badge bg={variant}>
      {normalizedStatus}
    </Badge>
  )
}
