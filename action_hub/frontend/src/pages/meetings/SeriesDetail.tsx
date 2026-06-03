import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap'
import api from '../../lib/api'
import { t } from '../../lib/i18n'
import { useAuth } from '../../contexts/AuthContext'
import { currentChinaDateISO, formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

interface UserOption {
  usr_id: number
  usr_display_name: string
  usr_username: string
}

interface SeriesDetailData {
  mtg_id: number
  mtg_title: string
  mtg_topic_id?: number | null
  mtg_description?: string | null
  mtg_visibility?: string
  mtg_created_by?: number | null
  topic_name?: string | null
  creator_name?: string | null
  instance_count?: number
  last_occurrence_date?: string | null
  default_participant_count?: number
  default_participants?: Array<{ msp_id: number; msp_user_id: number; usr_display_name: string; msp_kind: string }>
  occurrences?: Array<{
    min_id: number
    min_title: string
    min_date: string
    min_created_at?: string | null
    min_visibility?: string
    action_count?: number
    participant_count?: number
    participant_names?: string[]
    meeting_serial?: number
    meeting_display_id?: string | null
    occurrence_access?: boolean
  }>
}

interface TopicOption {
  top_id: number
  top_name: string
}

export default function SeriesDetail() {
  const { id } = useParams<{ id: string }>()
  const seriesId = Number(id || 0)
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [seriesForm, setSeriesForm] = useState({ title: '', description: '', topic_id: '', visibility: 'public' })
  const [showSeriesEditor, setShowSeriesEditor] = useState(false)
  const [showParticipantEditor, setShowParticipantEditor] = useState(false)
  const [participantForm, setParticipantForm] = useState<{ compulsory: number[]; optional: number[] }>({ compulsory: [], optional: [] })
  const [participantError, setParticipantError] = useState<string | null>(null)


  const [lockedMeta, setLockedMeta] = useState<{ mtg_title?: string; creator_name?: string } | null>(null)

  const { data: series, isLoading } = useQuery<SeriesDetailData>({
    queryKey: ['meeting-series', seriesId],
    queryFn: async () => {
      try {
        const res = await api.get(`/api/meetings/series/${seriesId}`)
        setLockedMeta(null)
        return res.data.data
      } catch (err: any) {
        if (err?.response?.status === 403 && err?.response?.data?.meta) {
          setLockedMeta(err.response.data.meta)
        }
        throw err
      }
    },
    enabled: !!seriesId,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 403) return false
      return failureCount < 3
    },
  })

  const { data: topics = [] } = useQuery<TopicOption[]>({
    queryKey: ['topics', 'series-detail'],
    queryFn: async () => (await api.get('/api/topics')).data.data || [],
  })

  const { data: allUsers = [] } = useQuery<UserOption[]>({
    queryKey: ['users', 'light'],
    queryFn: async () => (await api.get('/api/users')).data.data || [],
    enabled: showParticipantEditor,
  })

  const createOccurrenceMutation = useMutation({
    mutationFn: (payload: { date: string }) => api.post(`/api/meetings/series/${seriesId}/occurrences`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting-series', seriesId] })
    },
  })

  const updateSeriesMutation = useMutation({
    mutationFn: (payload: { title: string; description: string; topic_id: string; visibility: string }) => api.put(`/api/meetings/series/${seriesId}`, {
      title: payload.title,
      description: payload.description,
      topic_id: payload.topic_id ? Number(payload.topic_id) : null,
      visibility: payload.visibility,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting-series', seriesId] })
      setShowSeriesEditor(false)
    },
  })

  const updateParticipantsMutation = useMutation({
    mutationFn: (participants: Array<{ user_id: number; kind: string }>) =>
      api.put(`/api/meetings/series/${seriesId}/participants`, { participants }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting-series', seriesId] })
      setShowParticipantEditor(false)
      setParticipantError(null)
    },
    onError: (err: any) => {
      setParticipantError(err?.response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const openParticipantEditor = () => {
    const current = series?.default_participants || []
    setParticipantForm({
      compulsory: current.filter(p => p.msp_kind === 'Compulsory').map(p => p.msp_user_id),
      optional: current.filter(p => p.msp_kind !== 'Compulsory').map(p => p.msp_user_id),
    })
    setParticipantError(null)
    setShowParticipantEditor(true)
  }

  const toggleParticipant = (userId: number, kind: 'compulsory' | 'optional', checked: boolean) => {
    setParticipantForm(current => {
      const otherKind: 'compulsory' | 'optional' = kind === 'compulsory' ? 'optional' : 'compulsory'
      if (checked) {
        return {
          ...current,
          [kind]: [...current[kind], userId],
          [otherKind]: current[otherKind].filter(id => id !== userId),
        }
      }
      return { ...current, [kind]: current[kind].filter(id => id !== userId) }
    })
  }

  const canEditSeries = Boolean(user && (user.role === 'Admin' || Number(user.id) === Number(series?.mtg_created_by || 0)))

  const formatOccurrenceMeetingId = (occurrence: NonNullable<SeriesDetailData['occurrences']>[number]) => {
    if (occurrence.meeting_serial && occurrence.meeting_serial > 0) {
      return `#${occurrence.meeting_serial}`
    }
    const displayId = (occurrence.meeting_display_id || '').trim()
    if (displayId.includes('#')) {
      const suffix = displayId.split('#').pop()?.trim()
      if (suffix) return `#${suffix}`
    }
    if (displayId.startsWith('#')) {
      return displayId
    }
    return `#${occurrence.min_id}`
  }

  if (isLoading) {
    return <Spinner animation="border" />
  }

  if (lockedMeta) {
    return (
      <div className="text-center py-5">
        <div style={{ fontSize: '3rem' }}>🔒</div>
        <h3 className="mt-3">{lockedMeta.mtg_title || t('meetings.series', 'Meeting Series')}</h3>
        <p className="text-muted">
          {t('meetings.series_locked_detail', 'This meeting series is restricted. Only the creator and participants can view its content.')}
        </p>
        {lockedMeta.creator_name && (
          <p className="text-muted small">
            {t('meetings.contactCreator', 'Please contact {{owner}} to be added as a participant.', { owner: lockedMeta.creator_name })}
          </p>
        )}
        <Link to="/meetings/series" className="btn btn-outline-primary mt-2">
          {t('common.back', 'Back to Series List')}
        </Link>
      </div>
    )
  }

  if (!series) {
    return <Alert variant="warning">{t('common.notFound', 'Series not found')}</Alert>
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h2>{series.mtg_title}</h2>
          <div className="text-muted small d-flex flex-wrap gap-2">
            {series.topic_name && <span>{series.topic_name}</span>}
            {series.creator_name && <><span>&bull;</span><span>{t('meeting.createdBy', 'Created By')}: {series.creator_name}</span></>}
            {series.mtg_description && <><span>&bull;</span><span>{series.mtg_description}</span></>}
          </div>
        </div>
        <div className="d-flex align-items-center gap-2">
          {canEditSeries && (
            <Button
              variant="outline-primary"
              size="sm"
              onClick={() => {
                setSeriesForm({
                  title: series.mtg_title || '',
                  description: series.mtg_description || '',
                  topic_id: series.mtg_topic_id ? String(series.mtg_topic_id) : '',
                  visibility: series.mtg_visibility || 'public',
                })
                setShowSeriesEditor((current) => !current)
              }}
            >
              {showSeriesEditor ? t('common.close', 'Close') : t('common.edit', 'Edit')}
            </Button>
          )}
        </div>
      </div>

      {showSeriesEditor && canEditSeries && (
        <Card className="mb-3">
          <Card.Header>{t('meetings.editSeries', 'Edit Meeting Series')}</Card.Header>
          <Card.Body>
            <Form onSubmit={(event) => {
              event.preventDefault()
              updateSeriesMutation.mutate(seriesForm)
            }}>
              <Row className="g-3">
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>{t('meeting.title', 'Title')}</Form.Label>
                    <Form.Control value={seriesForm.title} onChange={(event) => setSeriesForm((current) => ({ ...current, title: event.target.value }))} required />
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.category', 'Category')}</Form.Label>
                    <Form.Select value={seriesForm.topic_id} onChange={(event) => setSeriesForm((current) => ({ ...current, topic_id: event.target.value }))}>
                      <option value="">{t('common.select', 'Select...')}</option>
                      {topics.map((topic) => <option key={topic.top_id} value={topic.top_id}>{topic.top_name}</option>)}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>{t('common.visibility', 'Visibility')}</Form.Label>
                    <Form.Select value={seriesForm.visibility} onChange={(event) => setSeriesForm((current) => ({ ...current, visibility: event.target.value }))}>
                      <option value="public">Public</option>
                      <option value="private">Private</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>{t('common.description', 'Description')}</Form.Label>
                    <Form.Control as="textarea" rows={3} value={seriesForm.description} onChange={(event) => setSeriesForm((current) => ({ ...current, description: event.target.value }))} />
                  </Form.Group>
                </Col>
              </Row>

              {updateSeriesMutation.isError && (
                <Alert variant="danger" className="mt-3 mb-0">
                  {((updateSeriesMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
                </Alert>
              )}

              <div className="d-flex gap-2 mt-3">
                <Button type="submit" disabled={updateSeriesMutation.isPending}>{updateSeriesMutation.isPending ? t('common.saving', 'Saving...') : t('common.save', 'Save')}</Button>
                <Button variant="secondary" onClick={() => setShowSeriesEditor(false)}>{t('common.cancel', 'Cancel')}</Button>
              </div>
            </Form>
          </Card.Body>
        </Card>
      )}

      {/* Default Participants — compact inline list */}
      <Card className="mb-3">
        <Card.Header className="py-2 d-flex justify-content-between align-items-center">
          <span>{t('meetings.participants', 'Default Participants')}</span>
          {canEditSeries && (
            <Button size="sm" variant="outline-secondary" onClick={() => showParticipantEditor ? setShowParticipantEditor(false) : openParticipantEditor()}>
              {showParticipantEditor ? t('common.close', 'Close') : t('common.edit', 'Edit')}
            </Button>
          )}
        </Card.Header>
        <Card.Body className="py-2">
          {!showParticipantEditor && (
            <div className="d-flex flex-wrap gap-2 align-items-center mb-2">
              {(series.default_participants || []).length === 0 && (
                <span className="text-muted small">{t('meetings.noParticipants', 'No default participants yet.')}</span>
              )}
              {(series.default_participants || []).map((participant) => (
                <Badge key={participant.msp_id} bg={participant.msp_kind === 'Compulsory' ? 'primary' : 'secondary'} className="d-flex align-items-center gap-1 py-1 px-2">
                  {participant.usr_display_name}
                  <span className="ms-1" style={{ fontSize: '0.7em', opacity: 0.8 }}>
                    {participant.msp_kind === 'Compulsory' ? t('meetings.compulsoryShort', 'C') : t('meetings.optionalShort', 'O')}
                  </span>
                </Badge>
              ))}
            </div>
          )}
          {showParticipantEditor && canEditSeries && (
            <Form onSubmit={(event) => {
              event.preventDefault()
              const participants = [
                ...participantForm.compulsory.map(id => ({ user_id: id, kind: 'Compulsory' })),
                ...participantForm.optional.map(id => ({ user_id: id, kind: 'Optional' })),
              ]
              updateParticipantsMutation.mutate(participants)
            }}>
              <Row className="g-3">
                <Col md={6}>
                  <Form.Label className="fw-semibold">{t('meetings.compulsoryParticipants', 'Compulsory Participants')}</Form.Label>
                  <div className="border rounded p-2" style={{ maxHeight: 220, overflowY: 'auto' }}>
                    {allUsers.map(u => (
                      <Form.Check
                        key={`comp-${u.usr_id}`}
                        id={`comp-${u.usr_id}`}
                        type="checkbox"
                        label={u.usr_display_name}
                        checked={participantForm.compulsory.includes(u.usr_id)}
                        onChange={e => toggleParticipant(u.usr_id, 'compulsory', e.target.checked)}
                        className="mb-1"
                      />
                    ))}
                  </div>
                </Col>
                <Col md={6}>
                  <Form.Label className="fw-semibold">{t('meetings.optionalParticipants', 'Optional Participants')}</Form.Label>
                  <div className="border rounded p-2" style={{ maxHeight: 220, overflowY: 'auto' }}>
                    {allUsers.map(u => (
                      <Form.Check
                        key={`opt-${u.usr_id}`}
                        id={`opt-${u.usr_id}`}
                        type="checkbox"
                        label={u.usr_display_name}
                        checked={participantForm.optional.includes(u.usr_id)}
                        onChange={e => toggleParticipant(u.usr_id, 'optional', e.target.checked)}
                        className="mb-1"
                      />
                    ))}
                  </div>
                </Col>
              </Row>
              {participantError && <Alert variant="danger" className="mt-2 mb-0 py-1 small">{participantError}</Alert>}
              <div className="d-flex gap-2 mt-3">
                <Button type="submit" size="sm" disabled={updateParticipantsMutation.isPending}>
                  {updateParticipantsMutation.isPending ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setShowParticipantEditor(false)}>{t('common.cancel', 'Cancel')}</Button>
              </div>
            </Form>
          )}
        </Card.Body>
      </Card>

      {/* Occurrences — full width table with inline create */}
      <Card>
        <Card.Header className="py-2 d-flex justify-content-between align-items-center">
          <span>{t('meetings.occurrences', 'Meetings')}</span>
          {canEditSeries && (
            <Button size="sm" disabled={createOccurrenceMutation.isPending}
              onClick={() => createOccurrenceMutation.mutate({ date: currentChinaDateISO() })}>
              {createOccurrenceMutation.isPending ? t('common.creating', 'Creating...') : t('meetings.newMeeting', '+ New Meeting')}
            </Button>
          )}
        </Card.Header>
        <Card.Body className="py-2">
          {createOccurrenceMutation.isError && (
            <Alert variant="danger" className="mb-2 py-1 small">
              {((createOccurrenceMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
            </Alert>
          )}
          <Table size="sm" responsive hover className="mb-0">
            <thead><tr><th>{t('meeting.id', 'Meeting ID')}</th><th>{t('meeting.date', 'Date')}</th><th>{t('meeting.title', 'Title')}</th><th className="text-center">{t('common.actions', 'Actions')}</th><th className="text-center">{t('meeting.participants', 'Participants')}</th><th></th></tr></thead>
            <tbody>
              {(series.occurrences || []).length === 0 && (
                <tr><td colSpan={6} className="text-muted text-center small py-3">{t('meetings.noOccurrences', 'No meetings yet. Click "+ New Meeting" to create one.')}</td></tr>
              )}
              {(series.occurrences || []).map((occurrence) => (
                <tr key={occurrence.min_id}>
                  <td className="text-nowrap fw-semibold">{formatOccurrenceMeetingId(occurrence)}</td>
                  <td className="text-nowrap">{formatChinaDateTimeNoSeconds(occurrence.min_created_at || occurrence.min_date)}</td>
                  <td>{occurrence.min_title}</td>
                  <td className="text-center"><Badge bg="light" text="dark">{occurrence.action_count || 0}</Badge></td>
                  <td className="text-center"><Badge bg="light" text="dark">{occurrence.participant_count || 0}</Badge></td>
                  <td className="text-end">
                    {occurrence.occurrence_access === false
                      ? (
                        <span
                          title={t('meetings.occurrence_locked', 'Access restricted — you are not a participant of this meeting')}
                          style={{ cursor: 'default', fontSize: '1.1em' }}
                        >🔒</span>
                      )
                      : <Link to={`/meetings/${occurrence.min_id}`} className="btn btn-outline-primary btn-sm py-0">{t('common.open', 'Open')}</Link>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  )
}
