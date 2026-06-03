import { Card } from 'react-bootstrap'
import { t } from '../lib/i18n'

export default function Gantt() {
  return (
    <div>
      <h2 className="mb-4">{t('nav.gantt', 'Gantt Chart')}</h2>
      <Card>
        <Card.Body>
          <p className="text-muted">{t('page.comingSoon', 'Coming soon - Gantt chart page')}</p>
        </Card.Body>
      </Card>
    </div>
  )
}