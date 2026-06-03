import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Modal, Form, Alert } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import { t } from '../../lib/i18n'

interface SeriesItem {
  mtg_id: number
  mtg_title: string
  mtg_description?: string | null
  mtg_visibility?: 'public' | 'private'
  series_access?: boolean
  topic_name?: string | null
  creator_name?: string | null
  mtg_target?: string | null
  instance_count?: number
  last_occurrence_date?: string | null
  default_participant_count?: number
  default_participants?: Array<{ msp_user_id: number }>
}

interface TopicOption {
  top_id: number
  top_name: string
}

function extractApiErrorMessage(err: any, fallback: string): string {
  const data = err?.response?.data
  const nestedMessage = data?.error?.message
  if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
    return nestedMessage
  }
  if (typeof data?.error === 'string' && data.error.trim()) {
    return data.error
  }
  if (typeof data?.message === 'string' && data.message.trim()) {
    return data.message
  }
  if (typeof err?.message === 'string' && err.message.trim()) {
    return err.message
  }
  return fallback
}

export default function SeriesList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', topic_id: '' })
  const [error, setError] = useState<string | null>(null)
  const [lockedMessage, setLockedMessage] = useState<string | null>(null)

  const createSeriesMutation = useMutation({
    mutationFn: async (payload: { title: string; description: string; topic_id: number }) => {
      const res = await api.post('/api/meetings/series', payload)
      return res.data.data
    },
    onSuccess: (data) => {
      setShowModal(false)
      setForm({ title: '', description: '', topic_id: '' })
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['meeting-series'] })
      if (data?.mtg_id) navigate(`/meetings/series/${data.mtg_id}`)
    },
    onError: (err: any) => {
      setError(extractApiErrorMessage(err, t('meetings.createSeriesFailed', 'Failed to create series')))
    },
  })

  const { data: series = [], isLoading } = useQuery<SeriesItem[]>({
    queryKey: ['meeting-series'],
    queryFn: async () => {
      const response = await api.get('/api/meetings/series')
      return response.data.data || []
    },
  })

  const { data: topics = [] } = useQuery<TopicOption[]>({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics')
      return response.data.data || []
    },
  })

  const columns: ColumnDef<SeriesItem>[] = [
    { accessorKey: 'mtg_title', header: t('meeting.title', 'Title') },
    {
      accessorKey: 'creator_name',
      header: t('meeting.createdBy', 'Created By'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      accessorKey: 'topic_name',
      header: t('meeting.topic', 'Category'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      id: 'occurrence_count',
      header: t('meeting.instances', 'Occurrences'),
      cell: ({ row }) => <Badge bg="info">{row.original.instance_count || 0}</Badge>,
    },
    {
      accessorKey: 'last_occurrence_date',
      header: t('meetings.lastOccurrence', 'Last Occurrence'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      id: 'access',
      header: t('common.access', 'Access'),
      cell: ({ row }) => {
        if (row.original.series_access !== false) {
          return <Badge bg="success">{t('common.open', 'Open')}</Badge>
        }
        return (
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={(event) => {
              event.stopPropagation()
              const owner = row.original.creator_name || t('meeting.createdBy', 'Created By')
              setLockedMessage(t('meetings.series_locked_message', 'This series is locked. Please contact {{owner}} to be added as a participant.', { owner }))
            }}
            title={t('meetings.series_locked', 'Locked')}
          >
            {'\uD83D\uDD12'}
          </Button>
        )
      },
    },
  ]

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('meetings.series', 'Meeting Series')}</h2>
        <Button variant="primary" onClick={() => setShowModal(true)}>
          {t('meetings.newSeries', 'New Series')}
        </Button>
      </div>
      {lockedMessage && (
        <Alert variant="warning" dismissible onClose={() => setLockedMessage(null)}>
          {lockedMessage}
        </Alert>
      )}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{t('meetings.newSeries', 'New Series')}</Modal.Title>
        </Modal.Header>
        <Form
          onSubmit={e => {
            e.preventDefault()
            if (!form.title.trim()) {
              setError(t('common.error', 'Error') + ': ' + t('meeting.title', 'Title') + ' required')
              return
            }
            if (!form.topic_id) {
              setError(t('common.error', 'Error') + ': ' + t('meeting.topic', 'Category') + ' required')
              return
            }
            createSeriesMutation.mutate({
              title: form.title.trim(),
              description: form.description.trim(),
              topic_id: Number(form.topic_id),
            })
          }}
        >
          <Modal.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            <Form.Group className="mb-3">
              <Form.Label>{t('meeting.title', 'Title')}</Form.Label>
              <Form.Control
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                required
                autoFocus
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('meeting.description', 'Description')}</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('meeting.topic', 'Category')}</Form.Label>
              <Form.Select
                value={form.topic_id}
                onChange={e => setForm(f => ({ ...f, topic_id: e.target.value }))}
                required
              >
                <option value="">{t('common.select', 'Select')}</option>
                {topics.map((topic) => (
                  <option key={topic.top_id} value={topic.top_id}>{topic.top_name}</option>
                ))}
              </Form.Select>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button type="submit" variant="primary" disabled={createSeriesMutation.isPending}>
              {t('common.save', 'Save')}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
      <CrudTable
        data={series}
        columns={columns}
        isLoading={isLoading}
        onRowClick={(row) => {
          if (row.series_access === false) {
            const owner = row.creator_name || t('meeting.createdBy', 'Created By')
            setLockedMessage(t('meetings.series_locked_message', 'This series is locked. Please contact {{owner}} to be added as a participant.', { owner }))
            return
          }
          navigate(`/meetings/series/${row.mtg_id}`)
        }}
        searchPlaceholder={t('common.search', 'Search series...')}
        pageSize={15}
      />
    </div>
  )
}
