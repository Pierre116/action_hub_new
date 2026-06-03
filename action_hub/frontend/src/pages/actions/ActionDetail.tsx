import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, Modal, ProgressBar, Row, Spinner, Table } from 'react-bootstrap'
import { t } from '../../lib/i18n'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import { addChinaDaysISO, formatChinaDate, formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

interface Action {
  act_id: number
  act_ref: string
  act_title: string
  act_desc: string
  act_tags?: string | null
  act_status: string
  act_priority: string
  act_deadline: string | null
  act_team_id?: number | null
  act_owner_id?: number | null
  act_created_by?: number | null
  creator_name?: string | null
  topic_name: string | null
  owner_name: string | null
  act_meeting_inst_id?: number | null
  meeting_title?: string | null
  meeting_date?: string | null
  can_change_status?: boolean
  can_edit?: boolean
  is_creator_only?: boolean
}

interface FeedbackEntry {
  afb_id: number
  afb_completion_pct: number | null
  afb_status: string | null
  afb_comment: string | null
  afb_blockers: string | null
  afb_est_date: string | null
  afb_created_at: string
  afb_meeting_inst_id?: number | null
  meeting_title?: string | null
  meeting_date?: string | null
  usr_display_name: string
}

const ACTION_STATUS_OPTIONS = ['Not started', 'On-track', 'Late', 'Done', 'Cancelled'] as const

function toFeedbackStatus(actionStatus: string): string {
  if (actionStatus === 'Done') return 'done'
  if (actionStatus === 'Cancelled') return 'cancelled'
  if (actionStatus === 'Late') return 'late'
  if (actionStatus === 'On-track') return 'on_track'
  return 'not_started'
}

function fromFeedbackStatus(feedbackStatus: string | null | undefined): string {
  if (feedbackStatus === 'done') return 'Done'
  if (feedbackStatus === 'cancelled') return 'Cancelled'
  if (feedbackStatus === 'late') return 'Late'
  if (feedbackStatus === 'on_track') return 'On-track'
  return 'Not started'
}

function normalizeActionStatusDisplay(actionStatus: string | null | undefined): string {
  const value = String(actionStatus || '').trim()
  if (value === 'Open' || value === 'Not started') return 'Not started'
  if (value === 'In Progress' || value === 'On-track') return 'On-track'
  if (value === 'On Hold' || value === 'Late' || value === 'Under Review') return 'Late'
  if (value === 'Done') return 'Done'
  if (value === 'Cancelled') return 'Cancelled'
  return 'Not started'
}

function toActionPatchStatus(progressStatus: string): string {
  if (progressStatus === 'Done') return 'Done'
  if (progressStatus === 'Cancelled') return 'Cancelled'
  if (progressStatus === 'Not started') return 'Open'
  return 'In Progress'
}

function statusBadgeForAction(actionStatus: string): string {
  if (actionStatus === 'Done') return 'success'
  if (actionStatus === 'Cancelled') return 'danger'
  if (actionStatus === 'Late') return 'warning'
  if (actionStatus === 'On-track') return 'info'
  return 'primary'
}

function formatFeedbackTimestamp(value: string | null | undefined): string {
  return formatChinaDateTimeNoSeconds(value)
}

interface Decision {
  mdc_id: number
  mdc_title: string
  mdc_body: string
  mdc_status: string
  mdc_meeting_title: string
  mdc_tags: string
  mdc_created_at: string
}

const statusColors: Record<string, string> = {
  Published: 'primary',
  Expired: 'secondary',
}

const STATUSES = ['Not started', 'On-track', 'Late', 'Done', 'Cancelled']
const PRIORITIES = ['High', 'Medium', 'Low']

function formatTags(tags?: string | null): string {
  return String(tags || '')
    .split(',')
    .map((tag) => tag.trim().replace(/^#+/, ''))
    .filter(Boolean)
    .map((tag) => `#${tag.toUpperCase()}`)
    .join(', ') || '-'
}

function defaultDeadlineDate(): string {
  return addChinaDaysISO(7)
}

export default function ActionDetail() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const meetingIdParam = searchParams.get('meeting_id')
  const isNewActionRoute = location.pathname === '/actions/new'
  const actionId = id === 'new' ? 0 : parseInt(id || '0', 10)
  const isNewAction = isNewActionRoute || id === 'new'
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    tags: '',
    status: 'Not started',
    priority: 'Medium',
    deadline: defaultDeadlineDate(),
    topic_id: '',
    owner_id: '',
    meeting_id: meetingIdParam || '',
  })

  const { data: topics = [] } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics')
      return response.data.data
    },
  })

  const { data: users = [] } = useQuery({
    queryKey: ['users-light'],
    queryFn: async () => {
      const response = await api.get('/api/users')
      return response.data.data
    },
  })

  // Fetch meeting details when creating new action from meeting (P10: S74)
  const { data: meetingForNewAction } = useQuery<{
    min_topic_id: number
    topic_name: string
    participants?: Array<{ mpa_user_id: number; usr_display_name: string }>
  }>({
    queryKey: ['meeting-for-new-action', meetingIdParam],
    queryFn: async () => {
      if (!meetingIdParam) return null as any
      const response = await api.get(`/api/meetings/${meetingIdParam}`)
      return response.data.data as { min_topic_id: number; topic_name: string }
    },
    enabled: isNewAction && !!meetingIdParam,
  })

  // Pre-populate topic from meeting when creating action from meeting (P10: S74)
  useEffect(() => {
    if (isNewAction && meetingForNewAction && meetingForNewAction.min_topic_id) {
      setFormData(prev => ({
        ...prev,
        topic_id: prev.topic_id || String(meetingForNewAction.min_topic_id),
      }))
    }
  }, [isNewAction, meetingForNewAction])

  useEffect(() => {
    if (!meetingIdParam || !meetingForNewAction?.participants?.length) {
      return
    }
    const allowedIds = new Set(meetingForNewAction.participants.map((participant) => String(participant.mpa_user_id)))
    setFormData((prev) => {
      let nextOwnerId = prev.owner_id
      if (!nextOwnerId || !allowedIds.has(nextOwnerId)) {
        const preferredParticipant = meetingForNewAction.participants?.find((participant) => participant.mpa_user_id === user?.id)
        nextOwnerId = String(preferredParticipant?.mpa_user_id || meetingForNewAction.participants?.[0]?.mpa_user_id || '')
      }
      if (nextOwnerId === prev.owner_id) {
        return prev
      }
      return { ...prev, owner_id: nextOwnerId }
    })
  }, [meetingIdParam, meetingForNewAction, user?.id])

  useEffect(() => {
    if (!isNewAction || !!meetingIdParam || !user?.id) {
      return
    }
    setFormData((prev) => {
      const nextOwnerId = String(user.id)
      if (prev.owner_id === nextOwnerId) {
        return prev
      }
      return { ...prev, owner_id: nextOwnerId }
    })
  }, [isNewAction, meetingIdParam, user?.id])

  const assignableUsers = meetingIdParam && meetingForNewAction?.participants?.length
    ? users.filter((entry: any) => meetingForNewAction.participants?.some((participant) => participant.mpa_user_id === entry.usr_id))
    : users.filter((entry: any) => entry.usr_id === user?.id)

  const [showEditModal, setShowEditModal] = useState(false)
  const [editForm, setEditForm] = useState({ title: '', description: '', status: 'Open', priority: 'Medium', deadline: '', cancel_reason: '', hold_reason: '' })
  const [editError, setEditError] = useState<string | null>(null)

  const openEditModal = () => {
    if (!action) return
    setEditForm({
      title: action.act_title || '',
      description: action.act_desc || '',
      status: action.act_status || 'Open',
      priority: action.act_priority || 'Medium',
      deadline: action.act_deadline ? action.act_deadline.split('T')[0] : '',
      cancel_reason: '',
      hold_reason: '',
    })
    setEditError(null)
    setShowEditModal(true)
  }

  const patchMutation = useMutation({
    mutationFn: async (data: typeof editForm) => {
      const payload: Record<string, unknown> = {
        title: data.title,
        description: data.description,
        status: data.status,
        deadline: data.deadline || null,
      }
      if (data.status === 'Cancelled') payload.cancel_reason = data.cancel_reason || 'Cancelled'
      if (data.status === 'On Hold') payload.hold_reason = data.hold_reason || 'On hold'
      return api.patch(`/api/actions/${actionId}`, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action', actionId] })
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      setShowEditModal(false)
    },
    onError: (err: any) => {
      setEditError(err?.response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/actions', {
      title: data.title,
      description: data.description,
      tags: data.tags || null,
      status: data.status,
      deadline: data.deadline || null,
      topic_id: data.topic_id ? parseInt(data.topic_id, 10) : null,
      lead_user_id: data.owner_id ? parseInt(data.owner_id, 10) : null,
      meeting_id: data.meeting_id ? parseInt(data.meeting_id, 10) : null,
    }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      const createdAction = response.data.data?.action ?? response.data.data
      const createdActionId = createdAction?.act_id
      navigate(createdActionId ? `/actions/${createdActionId}` : '/actions')
    },
  })

  const { data: action, isLoading: loadingAction } = useQuery<Action>({
    queryKey: ['action', actionId],
    queryFn: async () => {
      const response = await api.get(`/api/actions/${actionId}`)
      return (response.data.data?.action ?? response.data.data) as Action
    },
    enabled: !!actionId,
  })

  const { data: decisions = [], isLoading: loadingDecisions } = useQuery<Decision[]>({
    queryKey: ['action', actionId, 'decisions'],
    queryFn: async () => {
      const response = await api.get('/api/decisions/', { params: { action_id: actionId } })
      return response.data?.data || []
    },
    enabled: !!actionId,
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    createMutation.mutate(formData)
  }

  if (isNewAction) {
    return (
      <div>
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h2>{t('actions.new', 'Create Action')}</h2>
        </div>

        <Card>
          <Card.Body>
            <Form onSubmit={handleSubmit}>
              <Row className="mb-3">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('action.title', 'Title')} *</Form.Label>
                    <Form.Control
                      value={formData.title}
                      onChange={(event) => setFormData({ ...formData, title: event.target.value })}
                      required
                    />
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.status', 'Status')}</Form.Label>
                    <Form.Select
                      value={formData.status}
                      onChange={(event) => setFormData({ ...formData, status: event.target.value })}
                    >
                      {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>{t('common.description', 'Description')}</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      value={formData.description}
                      onChange={(event) => setFormData({ ...formData, description: event.target.value })}
                    />
                  </Form.Group>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={4}>
                  <Form.Group>
                    <Form.Label>{t('common.tags', 'Tags')}</Form.Label>
                    <Form.Control
                      value={formData.tags}
                      onChange={(event) => setFormData({ ...formData, tags: event.target.value })}
                      placeholder={t('actions.tagsPlaceholder', 'e.g. urgent, line3')}
                    />
                  </Form.Group>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.deadline', 'Deadline')}</Form.Label>
                    <Form.Control
                      type="date"
                      value={formData.deadline}
                      onChange={(event) => setFormData({ ...formData, deadline: event.target.value })}
                      required
                    />
                    <Form.Text className="text-muted">
                      {t('actions.deadline_required', 'Deadline is required to create an action.')}
                    </Form.Text>
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.category', 'Category')}</Form.Label>
                    <Form.Select
                      value={formData.topic_id}
                      onChange={(event) => setFormData({ ...formData, topic_id: event.target.value })}
                    >
                      <option value="">-- Select --</option>
                      {topics.map((topic: any) => <option key={topic.top_id} value={topic.top_id}>{topic.top_name}</option>)}
                    </Form.Select>
                    {meetingIdParam && formData.topic_id && (
                      <Form.Text className="text-muted">
                        {t('actions.topic_from_meeting', 'Category inherited from meeting')}
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.lead', 'Lead')}</Form.Label>
                    <Form.Select
                      value={formData.owner_id}
                      onChange={(event) => setFormData({ ...formData, owner_id: event.target.value })}
                      disabled={!meetingIdParam}
                    >
                      {assignableUsers.map((entry: any) => <option key={entry.usr_id} value={entry.usr_id}>{entry.usr_display_name}</option>)}
                    </Form.Select>
                    {meetingIdParam && (
                      <Form.Text className="text-muted">
                        {t('actions.owner_from_meeting_participants', 'Meeting actions can only be assigned to participants of the current meeting.')}
                      </Form.Text>
                    )}
                    {!meetingIdParam && (
                      <Form.Text className="text-muted">
                        {t('actions.owner_locked_to_creator', 'Actions created from this menu are owned by the current user.')}
                      </Form.Text>
                    )}
                  </Form.Group>
                </Col>
              </Row>

              {createMutation.isError && (
                <Alert variant="danger">
                  {((createMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
                </Alert>
              )}

              <div className="d-flex gap-2">
                <Button variant="primary" type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? t('common.saving', 'Saving...') : t('common.create', 'Create Action')}
                </Button>
                <Button variant="secondary" href="/actions">
                  {t('common.cancel', 'Cancel')}
                </Button>
              </div>
            </Form>
          </Card.Body>
        </Card>
      </div>
    )
  }

  if (loadingAction) {
    return (
      <div className="d-flex justify-content-center p-5">
        <Spinner animation="border" />
      </div>
    )
  }

  if (!action) {
    return <Alert variant="danger">{t('common.error')}</Alert>
  }

  const actionStatusDisplay = normalizeActionStatusDisplay(action.act_status)

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2>{action.act_ref}: {action.act_title}</h2>
          <span className="text-muted">{action.topic_name || '-'}</span>
        </div>
        {action.can_edit && (
          <Button variant="outline-primary" size="sm" onClick={openEditModal}>
            {t('common.edit', 'Edit')}
          </Button>
        )}
      </div>

      <Modal show={showEditModal} onHide={() => setShowEditModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{t('actions.edit', 'Edit Action')}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={(e) => { e.preventDefault(); patchMutation.mutate(editForm) }}>
          <Modal.Body>
            {editError && <Alert variant="danger">{editError}</Alert>}
            <Form.Group className="mb-3">
              <Form.Label>{t('action.title', 'Title')}</Form.Label>
              <Form.Control value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} required />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('common.description', 'Description')}</Form.Label>
              <Form.Control as="textarea" rows={3} value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
            </Form.Group>
            <Row className="mb-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label>{t('common.status', 'Status')}</Form.Label>
                  <Form.Select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                    <option value="Open">{t('action.status.Open', 'Not started')}</option>
                    <option value="In Progress">{t('action.status.onTrack', 'On-track')}</option>
                    <option value="On Hold">{t('action.status.UnderReview', 'Late / On Hold')}</option>
                    <option value="Done">{t('action.status.Done', 'Done')}</option>
                    <option value="Cancelled">{t('action.status.Cancelled', 'Cancelled')}</option>
                  </Form.Select>
                </Form.Group>
              </Col>

            </Row>
            <Form.Group className="mb-3">
              <Form.Label>{t('common.deadline', 'Deadline')}</Form.Label>
              <Form.Control type="date" value={editForm.deadline} onChange={(e) => setEditForm({ ...editForm, deadline: e.target.value })} />
            </Form.Group>
            {editForm.status === 'Cancelled' && (
              <Form.Group className="mb-3">
                <Form.Label>{t('action.cancelReason', 'Cancel Reason')} *</Form.Label>
                <Form.Control as="textarea" rows={2} value={editForm.cancel_reason} onChange={(e) => setEditForm({ ...editForm, cancel_reason: e.target.value })} placeholder={t('action.cancelReasonPlaceholder', 'Reason for cancelling...')} />
              </Form.Group>
            )}
            {editForm.status === 'On Hold' && (
              <Form.Group className="mb-3">
                <Form.Label>{t('action.holdReason', 'Hold Reason')} *</Form.Label>
                <Form.Control as="textarea" rows={2} value={editForm.hold_reason} onChange={(e) => setEditForm({ ...editForm, hold_reason: e.target.value })} placeholder={t('action.holdReasonPlaceholder', 'Reason for putting on hold...')} />
              </Form.Group>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>{t('common.cancel', 'Cancel')}</Button>
            <Button variant="primary" type="submit" disabled={patchMutation.isPending}>
              {patchMutation.isPending ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <Card className="mb-4">
        <Card.Body>
          <h5>{t('action.detail', 'Action Details')}</h5>
          <dl className="row mb-0">
            <dt className="col-sm-3">{t('action.title', 'Title')}</dt>
            <dd className="col-sm-9">{action.act_title || '-'}</dd>
            <dt className="col-sm-3">{t('common.status', 'Status')}</dt>
            <dd className="col-sm-9"><Badge bg={statusBadgeForAction(actionStatusDisplay)}>{actionStatusDisplay}</Badge></dd>
            <dt className="col-sm-3">{t('common.tags', 'Tags')}</dt>
            <dd className="col-sm-9">{formatTags(action.act_tags)}</dd>
            <dt className="col-sm-3">{t('common.lead', 'Lead')}</dt>
            <dd className="col-sm-9">{action.owner_name || '-'}</dd>
            <dt className="col-sm-3">{t('common.createdBy', 'Created by')}</dt>
            <dd className="col-sm-9">{action.creator_name || '-'}</dd>
            <dt className="col-sm-3">{t('common.category', 'Category')}</dt>
            <dd className="col-sm-9">{action.topic_name || '-'}</dd>
            <dt className="col-sm-3">{t('common.deadline', 'End Date')}</dt>
            <dd className="col-sm-9">{formatChinaDate(action.act_deadline)}</dd>
            <dt className="col-sm-3">{t('common.description', 'Description')}</dt>
            <dd className="col-sm-9">{action.act_desc || '-'}</dd>
            {action.meeting_title && (
              <>
                <dt className="col-sm-3">{t('meetings.title', 'Meeting')}</dt>
                <dd className="col-sm-9">
                  {action.meeting_title}
                  {action.meeting_date && (
                    <span className="text-muted small ms-2">({formatChinaDate(action.meeting_date)})</span>
                  )}
                </dd>
              </>
            )}
          </dl>
        </Card.Body>
      </Card>

      {/* ── Quick Feedback Widget ── */}
      {!isNewAction && action && (
        <FeedbackWidget actionId={action.act_id} meetingInstId={action.act_meeting_inst_id || null} actionStatus={actionStatusDisplay} />
      )}

      {(loadingDecisions || decisions.length > 0) && (
        <Card>
          <Card.Header>{t('decisions.related', 'Related Decisions')}</Card.Header>
          <Card.Body className="p-0">
            {loadingDecisions ? (
              <div className="text-center p-3">
                <Spinner animation="border" size="sm" />
              </div>
            ) : decisions.length === 0 ? (
              <div className="text-center p-3 text-muted">{t('decisions.no_decisions', 'No decisions found.')}</div>
            ) : (
              <Table responsive hover className="mb-0">
                <thead>
                  <tr>
                    <th>{t('common.title', 'Title')}</th>
                    <th>{t('common.status', 'Status')}</th>
                    <th>{t('meetings.title', 'Meeting')}</th>
                    <th>{t('common.date', 'Date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {decisions.map((decision) => (
                    <tr key={decision.mdc_id}>
                      <td>
                        <strong>{decision.mdc_title}</strong>
                        {decision.mdc_body && <div className="small text-muted">{decision.mdc_body.substring(0, 50)}...</div>}
                      </td>
                      <td>
                        <Badge bg={statusColors[decision.mdc_status] || 'secondary'}>{decision.mdc_status}</Badge>
                      </td>
                      <td>{decision.mdc_meeting_title || '-'}</td>
                      <td>{decision.mdc_created_at?.split(' ')[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

/* ── Feedback sub-component ── */
function FeedbackWidget({ actionId, meetingInstId, actionStatus }: { actionId: number; meetingInstId: number | null; actionStatus: string }) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [fb, setFb] = useState({ completion_pct: 50, status: 'Not started', comment: '', blockers: '' })

  const { data: feedbackList = [] } = useQuery<FeedbackEntry[]>({
    queryKey: ['action-feedback', actionId],
    queryFn: async () => {
      const res = await api.get(`/api/actions/${actionId}/feedback`)
      return res.data.data || []
    },
  })

  const submitMutation = useMutation({
    mutationFn: async (data: typeof fb) => {
      await api.post(`/api/actions/${actionId}/feedback`, {
        meeting_inst_id: meetingInstId,
        completion_pct: data.completion_pct,
        status: toFeedbackStatus(data.status),
        comment: data.comment || null,
        blockers: data.blockers || null,
      })

      const nextActionStatus = toActionPatchStatus(data.status)
      const actionPatchPayload: Record<string, unknown> = {
        status: nextActionStatus,
        completion_pct: data.completion_pct,
      }

      if (nextActionStatus === 'Cancelled') {
        actionPatchPayload.cancel_reason = data.blockers || data.comment || 'Cancelled from progress update'
      }

      await api.patch(`/api/actions/${actionId}`, actionPatchPayload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action-feedback', actionId] })
      queryClient.invalidateQueries({ queryKey: ['action', actionId] })
      setShowForm(false)
    },
  })

  const latest = feedbackList[0]
  // Use the actual action status (from the action object) as the authoritative source,
  // falling back to the latest feedback status if action status is not available.
  const latestActionStatus = actionStatus

  return (
    <Card className="mb-4">
      <Card.Header className="d-flex justify-content-between align-items-center py-2">
        <strong className="small">{t('action.progressUpdate', 'Progress Update')}</strong>
        <Button variant="outline-primary" size="sm" onClick={() => {
          if (latest) setFb({ completion_pct: latest.afb_completion_pct ?? 50, status: fromFeedbackStatus(latest.afb_status), comment: '', blockers: latest.afb_blockers || '' })
          else setFb((prev) => ({ ...prev, status: normalizeActionStatusDisplay(actionStatus) }))
          setShowForm(!showForm)
        }}>
          {showForm ? t('common.cancel', 'Cancel') : t('action.updateProgress', 'Update Progress')}
        </Button>
      </Card.Header>
      <Card.Body className="py-2">
        {/* Latest feedback summary */}
        {latest ? (
          <div className="d-flex align-items-center gap-3 mb-2 flex-wrap">
            <div style={{ minWidth: 120 }}>
              <ProgressBar now={latest.afb_completion_pct ?? 0} label={`${latest.afb_completion_pct ?? 0}%`} variant={statusBadgeForAction(latestActionStatus)} style={{ height: 20 }} />
            </div>
            <Badge bg={statusBadgeForAction(latestActionStatus)}>{latestActionStatus}</Badge>
            {latest.afb_comment && <span className="small text-muted">{latest.afb_comment}</span>}
            {latest.afb_blockers && <span className="small text-danger">Blockers: {latest.afb_blockers}</span>}
            {latest.afb_est_date && <span className="small text-info">{t('action.estDate', 'Est. date')}: {formatChinaDate(latest.afb_est_date)}</span>}
            {latest.meeting_title && (
              <span className="small text-primary">
                {latest.meeting_title}{latest.meeting_date ? ` (${formatChinaDate(latest.meeting_date)})` : ''}
              </span>
            )}
            <span className="small text-muted ms-auto">{latest.usr_display_name} &mdash; {formatFeedbackTimestamp(latest.afb_created_at)}</span>
          </div>
        ) : (
          <p className="text-muted small mb-2">{t('action.noFeedback', 'No progress update yet. Click "Update Progress" to add one.')}</p>
        )}

        {/* Submit form */}
        {showForm && (
          <Form onSubmit={(e) => { e.preventDefault(); submitMutation.mutate(fb) }} className="border-top pt-2">
            <Row className="g-2 align-items-end">
              <Col md={2}>
                <Form.Label className="small mb-0">{t('action.completion', 'Completion')}</Form.Label>
                <div className="d-flex align-items-center gap-1">
                  <Form.Range min={0} max={100} step={10} value={fb.completion_pct}
                    onChange={(e) => setFb({ ...fb, completion_pct: parseInt(e.target.value) })} />
                  <span className="small fw-bold" style={{ minWidth: 32 }}>{fb.completion_pct}%</span>
                </div>
              </Col>
              <Col md={2}>
                <Form.Label className="small mb-0">{t('action.progressStatus', 'Status')}</Form.Label>
                <Form.Select size="sm" value={fb.status} onChange={(e) => setFb({ ...fb, status: e.target.value })}>
                  {ACTION_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Label className="small mb-0">{t('action.comment', 'Comment')}</Form.Label>
                <Form.Control size="sm" value={fb.comment} onChange={(e) => setFb({ ...fb, comment: e.target.value })}
                  placeholder={t('action.feedbackCommentPlaceholder', 'What progress was made?')} />
              </Col>
              <Col md={3}>
                <Form.Label className="small mb-0">{t('action.blockers', 'Blockers')}</Form.Label>
                <Form.Control size="sm" value={fb.blockers} onChange={(e) => setFb({ ...fb, blockers: e.target.value })}
                  placeholder={t('action.blockersPlaceholder', 'Any blockers?')} />
              </Col>
              <Col md={2}>
                <Button type="submit" size="sm" variant="primary" disabled={submitMutation.isPending} className="w-100">
                  {submitMutation.isPending ? '...' : t('common.save', 'Save')}
                </Button>
              </Col>
            </Row>
            {submitMutation.isError && (
              <Alert variant="danger" className="py-1 mt-2 small">
                {((submitMutation.error as any)?.response?.data?.error?.message)
                  || ((submitMutation.error as any)?.response?.data?.error)
                  || t('action.progressSaveFailed', 'Failed to save progress update')}
              </Alert>
            )}
          </Form>
        )}

        {/* History (last 3 entries) */}
        {feedbackList.length > 1 && (
          <div className="border-top mt-2 pt-2">
            <div className="small text-muted mb-1">{t('action.feedbackHistory', 'Previous updates:')}</div>
            {feedbackList.slice(1, 4).map((entry) => {
              const histActionStatus = fromFeedbackStatus(entry.afb_status)
              return (
                <div key={entry.afb_id} className="d-flex align-items-center gap-2 py-1 flex-wrap" style={{ fontSize: '0.8rem' }}>
                  <Badge bg={statusBadgeForAction(histActionStatus)} style={{ fontSize: '0.65rem' }}>{histActionStatus}</Badge>
                  <span>{entry.afb_completion_pct ?? 0}%</span>
                  {entry.afb_comment && <span className="text-muted">{entry.afb_comment}</span>}
                  {entry.afb_blockers && <span className="text-danger">Blockers: {entry.afb_blockers}</span>}
                  {entry.afb_est_date && <span className="text-info">{t('action.estDate', 'Est. date')}: {formatChinaDate(entry.afb_est_date)}</span>}
                  {entry.meeting_title && <span className="text-primary">{entry.meeting_title}</span>}
                  <span className="text-muted ms-auto">{entry.usr_display_name} &mdash; {formatFeedbackTimestamp(entry.afb_created_at)}</span>
                </div>
              )
            })}
          </div>
        )}
      </Card.Body>
    </Card>
  )
}
