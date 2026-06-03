import { useQuery } from '@tanstack/react-query'
import { Alert, Badge, Card, Col, Row, Spinner, Table } from 'react-bootstrap'
import api from '../../lib/api'
import KpiCard from '../../components/shared/KpiCard'
import { t } from '../../lib/i18n'

interface TopicSummary {
  top_id: number
  top_code: string
  top_name: string
  open_count: number
  in_progress_count: number
  overdue_count: number
  done_count: number
  total_count: number
}

interface DecisionItem {
  mdc_status: string
  mdc_category_id?: number | null
  mdc_secondary_category_id?: number | null
}

export default function BusinessTheme() {
  const { data: topicsData = [], isLoading: topicsLoading } = useQuery<TopicSummary[]>({
    queryKey: ['dashboard', 'topics', 'summary'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/topics/summary')
      return (response.data.data || []).map((row: any) => ({
        top_id: row.top_id,
        top_code: row.top_code,
        top_name: row.top_name,
        open_count: row.open || 0,
        in_progress_count: row.in_progress || 0,
        overdue_count: row.overdue || 0,
        done_count: row.done || 0,
        total_count: row.total || 0,
      })) as TopicSummary[]
    },
  })

  const { data: decisions = [] } = useQuery<DecisionItem[]>({
    queryKey: ['dashboard', 'decisions-all-for-topic-counters'],
    queryFn: async () => {
      const response = await api.get('/api/decisions/', { params: { limit: 1000, offset: 0 } })
      return response.data?.data || []
    },
  })

  const { data: decisionDashboard } = useQuery({
    queryKey: ['dashboard', 'decisions', 'all'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/decisions', { params: { scope: 'all', limit: 6 } })
      return response.data.data
    },
  })

  if (topicsLoading) {
    return <div className="d-flex justify-content-center py-5"><Spinner animation="border" /></div>
  }

  const totalActions = topicsData.reduce((sum, topic) => sum + topic.total_count, 0)
  const totalOpen = topicsData.reduce((sum, topic) => sum + topic.open_count, 0)
  const totalOnTrack = topicsData.reduce((sum, topic) => sum + topic.in_progress_count, 0)
  const totalOverdue = topicsData.reduce((sum, topic) => sum + topic.overdue_count, 0)
  const totalDone = topicsData.reduce((sum, topic) => sum + topic.done_count, 0)

  const activeDecisionsByTopic = new Map<number, number>()
  for (const decision of decisions) {
    if (decision.mdc_status !== 'Published') continue
    const keys = [decision.mdc_category_id, decision.mdc_secondary_category_id].filter((v): v is number => !!v)
    keys.forEach((id) => {
      activeDecisionsByTopic.set(id, (activeDecisionsByTopic.get(id) || 0) + 1)
    })
  }
  const totalActiveDecisions = Array.from(activeDecisionsByTopic.values()).reduce((a, b) => a + b, 0)
  const decisionKpis = decisionDashboard?.kpis || {}

  return (
    <div>
      <h2 className="mb-4">{t('dashboard.businessTheme', 'Business Theme Dashboard')}</h2>

      <Row className="mb-4 g-3 flex-nowrap overflow-auto">
        <Col style={{ minWidth: 220 }}><KpiCard title={t('dashboard.totalActions', 'Total Actions')} value={totalActions} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('action.status.Open', 'Open')} value={totalOpen} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('action.status.onTrack', 'On-track')} value={totalOnTrack} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('dashboard.overdue', 'Overdue')} value={totalOverdue} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('action.status.completed', 'Completed')} value={totalDone} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('dashboard.activeDecisions', 'Active Decisions')} value={totalActiveDecisions} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('decisions.status_published', 'Published Decisions')} value={decisionKpis.published || 0} /></Col>
        <Col style={{ minWidth: 220 }}><KpiCard title={t('decisions.status_expired', 'Expired Decisions')} value={decisionKpis.expired || 0} /></Col>
      </Row>

      <Card>
        <Card.Header>{t('dashboard.allTopicsSummary', 'All Business Themes Summary')}</Card.Header>
        <Card.Body>
          {topicsData.length === 0 ? (
            <Alert variant="light" className="mb-0">{t('dashboard.noTopics', 'No business themes found.')}</Alert>
          ) : (
            <Table responsive hover className="mb-0">
              <thead>
                <tr>
                  <th>{t('dashboard.topic', 'Business Theme')}</th>
                  <th>{t('dashboard.open', 'Open')}</th>
                  <th>{t('dashboard.inProgress', 'On-track')}</th>
                  <th>{t('dashboard.overdue', 'Overdue')}</th>
                  <th>{t('dashboard.done', 'Completed')}</th>
                  <th>{t('dashboard.activeDecisions', 'Active Decisions')}</th>
                  <th>{t('dashboard.total', 'Total')}</th>
                </tr>
              </thead>
              <tbody>
                {topicsData.map((topic) => (
                  <tr key={topic.top_code}>
                    <td>{topic.top_name}</td>
                    <td><Badge bg="primary">{topic.open_count}</Badge></td>
                    <td><Badge bg="warning" text="dark">{topic.in_progress_count}</Badge></td>
                    <td><Badge bg={topic.overdue_count > 0 ? 'danger' : 'secondary'}>{topic.overdue_count}</Badge></td>
                    <td><Badge bg="success">{topic.done_count}</Badge></td>
                    <td><Badge bg="info">{activeDecisionsByTopic.get(topic.top_id) || 0}</Badge></td>
                    <td><Badge bg="dark">{topic.total_count}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}
