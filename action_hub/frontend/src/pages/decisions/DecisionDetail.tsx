import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Spinner, Table } from 'react-bootstrap'
import { t } from '../../lib/i18n'
import api from '../../lib/api'
import { formatChinaDate } from '../../lib/dateTime'

interface DecisionDetailData {
  mdc_id: number
  mdc_title: string
  mdc_body: string
  mdc_context?: string | null
  mdc_reason?: string | null
  mdc_status: string
  mdc_meeting_id?: number | null
  mdc_category_id?: number | null
  mdc_secondary_category_id?: number | null
  mdc_tags?: string | null
  mdc_decided_at?: string | null
  mdc_created_at?: string | null
  mdc_updated_at?: string | null
  mdc_expires_at?: string | null
  mdc_status_changed_at?: string | null
  creator_name?: string | null
  category_name?: string | null
  secondary_category_name?: string | null
  revision_count?: number
  last_revised_at?: string | null
  meeting_title?: string | null
  series_title?: string | null
  occurrence_date?: string | null
}

interface DecisionRevision {
  mdr_id: number
  mdr_decision_id: number
  mdr_title: string
  mdr_body: string
  mdr_updated_by?: number | null
  mdr_updated_at: string
  updated_by_name?: string | null
}

const statusColors: Record<string, string> = {
  Published: 'primary',
  Expired: 'secondary',
}

function inferYear(value?: string | null): number {
  const parsed = value ? new Date(value) : null
  if (parsed && !Number.isNaN(parsed.getTime())) {
    return parsed.getFullYear()
  }
  return new Date().getFullYear()
}

function formatDecisionRef(decision: DecisionDetailData): string {
  return `DEC-${inferYear(decision.mdc_created_at)}-${String(decision.mdc_id).padStart(5, '0')}`
}

function formatTags(tags?: string | null): string {
  return String(tags || '')
    .split(',')
    .map((tag) => tag.trim().replace(/^#+/, ''))
    .filter(Boolean)
    .map((tag) => `#${tag.toUpperCase()}`)
    .join(', ') || '-'
}

export default function DecisionDetail() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const decisionId = Number(id || 0)

  const { data: decision, isLoading } = useQuery<DecisionDetailData>({
    queryKey: ['decision', decisionId],
    queryFn: async () => {
      const response = await api.get(`/api/decisions/${decisionId}`)
      return response.data?.data as DecisionDetailData
    },
    enabled: Number.isFinite(decisionId) && decisionId > 0,
  })

  const { data: revisions = [], isLoading: revisionsLoading } = useQuery<DecisionRevision[]>({
    queryKey: ['decision', decisionId, 'revisions'],
    queryFn: async () => {
      const response = await api.get(`/api/decisions/${decisionId}/revisions`)
      return (response.data?.data || []) as DecisionRevision[]
    },
    enabled: Number.isFinite(decisionId) && decisionId > 0,
  })

  const meetingLink = useMemo(() => {
    const meetingId = decision?.mdc_meeting_id
    if (!meetingId) return null
    return `/meetings/${meetingId}`
  }, [decision?.mdc_meeting_id])

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
      return
    }
    navigate('/decisions')
  }

  if (!decisionId || Number.isNaN(decisionId)) {
    return <Alert variant="danger">{t('common.error', 'Error')}</Alert>
  }

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center p-5">
        <Spinner animation="border" />
      </div>
    )
  }

  if (!decision) {
    return <Alert variant="danger">{t('common.error', 'Error')}</Alert>
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="mb-1">{formatDecisionRef(decision)}</h2>
          <div className="text-muted">{decision.mdc_title}</div>
        </div>
        <Button variant="outline-secondary" size="sm" onClick={handleBack}>
          {t('common.back', 'Back')}
        </Button>
      </div>

      <Card>
        <Card.Body>
          <dl className="row mb-0">
            <dt className="col-sm-3">{t('common.id', 'ID')}</dt>
            <dd className="col-sm-9">{formatDecisionRef(decision)}</dd>

            <dt className="col-sm-3">{t('common.title', 'Title')}</dt>
            <dd className="col-sm-9">{decision.mdc_title || '-'}</dd>

            <dt className="col-sm-3">{t('common.status', 'Status')}</dt>
            <dd className="col-sm-9">
              <Badge bg={statusColors[decision.mdc_status] || 'secondary'}>{decision.mdc_status}</Badge>
            </dd>

            <dt className="col-sm-3">{t('decisions.content', 'Content')}</dt>
            <dd className="col-sm-9">{decision.mdc_body || '-'}</dd>

            <dt className="col-sm-3">{t('decisions.context', 'Context')}</dt>
            <dd className="col-sm-9">{decision.mdc_context || '-'}</dd>

            <dt className="col-sm-3">{t('decisions.reason', 'Why')}</dt>
            <dd className="col-sm-9">{decision.mdc_reason || '-'}</dd>

            <dt className="col-sm-3">{t('common.tags', 'Tags')}</dt>
            <dd className="col-sm-9">{formatTags(decision.mdc_tags)}</dd>

            <dt className="col-sm-3">{t('common.category', 'Category')}</dt>
            <dd className="col-sm-9">{decision.category_name || '-'}</dd>

            <dt className="col-sm-3">{t('decisions.secondary_category', 'Secondary Category')}</dt>
            <dd className="col-sm-9">{decision.secondary_category_name || '-'}</dd>

            <dt className="col-sm-3">{t('common.createdBy', 'Created by')}</dt>
            <dd className="col-sm-9">{decision.creator_name || '-'}</dd>

            <dt className="col-sm-3">{t('meetings.meeting', 'Meeting')}</dt>
            <dd className="col-sm-9">
              {meetingLink ? (
                <Link to={meetingLink}>
                  {decision.series_title || decision.meeting_title || `#${decision.mdc_meeting_id}`}
                  {decision.occurrence_date ? ` (${formatChinaDate(decision.occurrence_date)})` : ''}
                </Link>
              ) : '-'}
            </dd>

            <dt className="col-sm-3">{t('common.createdAt', 'Created')}</dt>
            <dd className="col-sm-9">{formatChinaDate(decision.mdc_created_at)}</dd>

            <dt className="col-sm-3">{t('common.updatedAt', 'Updated')}</dt>
            <dd className="col-sm-9">{formatChinaDate(decision.mdc_updated_at)}</dd>

            <dt className="col-sm-3">{t('decisions.revisionHistory', 'Revision History')}</dt>
            <dd className="col-sm-9">
              {(decision.revision_count || 0) > 0
                ? `${decision.revision_count} · ${formatChinaDate(decision.last_revised_at)}`
                : t('decisions.noRevisions', 'No revision history available.')}
            </dd>

            <dt className="col-sm-3">{t('decisions.expiredAt', 'Expired At')}</dt>
            <dd className="col-sm-9">{formatChinaDate(decision.mdc_status_changed_at || decision.mdc_expires_at)}</dd>
          </dl>
        </Card.Body>
      </Card>

      <Card className="mt-4">
        <Card.Header>{t('decisions.revisionHistory', 'Revision History')}</Card.Header>
        <Card.Body className="p-0">
          {revisionsLoading ? (
            <div className="d-flex justify-content-center p-4">
              <Spinner animation="border" size="sm" />
            </div>
          ) : revisions.length === 0 ? (
            <p className="text-muted mb-0 p-4">{t('decisions.noRevisions', 'No revision history available.')}</p>
          ) : (
            <Table responsive hover className="mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: 72 }}>#</th>
                  <th>{t('common.title', 'Title')}</th>
                  <th>{t('decisions.content', 'Content')}</th>
                  <th style={{ width: 180 }}>{t('decisions.revisedBy', 'Revised By')}</th>
                  <th style={{ width: 140 }}>{t('decisions.revisedAt', 'Revised At')}</th>
                </tr>
              </thead>
              <tbody>
                {revisions.map((revision, index) => (
                  <tr key={revision.mdr_id}>
                    <td>{revisions.length - index}</td>
                    <td>{revision.mdr_title || '-'}</td>
                    <td>{revision.mdr_body || '-'}</td>
                    <td>{revision.updated_by_name || '-'}</td>
                    <td>{formatChinaDate(revision.mdr_updated_at)}</td>
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
