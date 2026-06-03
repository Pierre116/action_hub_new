import { Card } from 'react-bootstrap'

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
}

export default function KpiCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
}: KpiCardProps) {
  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-success'
      case 'down':
        return 'text-danger'
      default:
        return 'text-muted'
    }
  }

  return (
    <Card className="h-100 border-0" style={{ backgroundColor: '#f5f9ff' }}>
      <Card.Body className="py-3 px-3">
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <Card.Title as="h6" className="text-dark mb-2 fw-semibold" style={{ fontSize: '0.95rem' }}>
              {title}
            </Card.Title>
            <h2 className="mb-0 fw-bold" style={{ fontSize: '2rem', lineHeight: 1.1 }}>{value}</h2>
            {subtitle && (
              <small className="text-secondary">{subtitle}</small>
            )}
          </div>
          {icon && (
            <div className="text-secondary">{icon}</div>
          )}
        </div>
        {trend && trendValue && (
          <div className={`mt-2 ${getTrendColor()}`}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
          </div>
        )}
      </Card.Body>
    </Card>
  )
}
