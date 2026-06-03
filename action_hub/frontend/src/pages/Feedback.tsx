import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Row, Col, Card, Form, Button, Badge, Alert } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../lib/api'
import CrudTable from '../components/shared/CrudTable'
import { t } from '../lib/i18n'
import { formatChinaDate } from '../lib/dateTime'

interface Feedback {
  fbk_id: number
  fbk_category: string
  fbk_page: string
  fbk_priority: string
  fbk_status: string
  fbk_title: string
  fbk_description: string
  fbk_created_at: string
}

const CATEGORIES = [
  { value: 'Bug', label: 'Bug Report' },
  { value: 'Feature', label: 'Feature Request' },
  { value: 'Usability', label: 'Usability' },
  { value: 'General', label: 'General' },
]

const PRIORITIES = [
  { value: 'Low', label: 'Low' },
  { value: 'Medium', label: 'Medium' },
  { value: 'High', label: 'High' },
]

const STATUS_COLORS: Record<string, string> = {
  'New': 'primary',
  'Acknowledged': 'info',
  'In Progress': 'warning',
  'Resolved': 'success',
  'Declined': 'secondary',
}

export default function Feedback() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    category: 'Feature',
    priority: 'Medium',
    title: '',
    description: '',
  })
  const [error, setError] = useState('')

  // Fetch feedback
  const { data: feedback = [], isLoading } = useQuery({
    queryKey: ['feedback'],
    queryFn: async () => {
      const response = await api.get('/api/feedback')
      return response.data.data as Feedback[]
    },
  })

  // Create feedback mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => {
      const form = new FormData()
      form.append('category', data.category)
      form.append('priority', data.priority)
      form.append('title', data.title)
      form.append('description', data.description)
      return api.post('/api/feedback', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
      setShowForm(false)
      setFormData({
        category: 'Feature',
        priority: 'Medium',
        title: '',
        description: '',
      })
      setError('')
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!formData.title.trim()) {
      setError(t('feedback.titleRequired', 'Title is required'))
      return
    }
    createMutation.mutate(formData)
  }

  const columns: ColumnDef<Feedback>[] = [
    {
      accessorKey: 'fbk_title',
      header: t('feedback.title', 'Title'),
    },
    {
      accessorKey: 'fbk_category',
      header: t('feedback.category', 'Category'),
      cell: ({ getValue }) => {
        const cat = getValue() as string
        return <Badge bg="secondary">{cat}</Badge>
      },
    },
    {
      accessorKey: 'fbk_priority',
      header: t('feedback.priority', 'Priority'),
      cell: ({ getValue }) => {
        const pri = getValue() as string
        const colors: Record<string, string> = {
          low: 'success',
          medium: 'warning',
          high: 'danger',
          urgent: 'dark',
        }
        return <Badge bg={colors[pri] || 'secondary'}>{pri}</Badge>
      },
    },
    {
      accessorKey: 'fbk_status',
      header: t('common.status', 'Status'),
      cell: ({ getValue }) => {
        const status = getValue() as string
        return <Badge bg={STATUS_COLORS[status] || 'secondary'}>{status}</Badge>
      },
    },
    {
      accessorKey: 'fbk_created_at',
      header: t('common.date', 'Date'),
      cell: ({ row }) => {
        const date = row.original.fbk_created_at
        return formatChinaDate(date)
      },
    },
  ]

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.feedback', 'Feedback')}</h2>
        <Button variant="primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? t('common.cancel', 'Cancel') : t('feedback.submit', 'Submit Feedback')}
        </Button>
      </div>

      {showForm && (
        <Card className="mb-4">
          <Card.Header>{t('feedback.submitNew', 'Submit New Feedback')}</Card.Header>
          <Card.Body>
            <Form onSubmit={handleSubmit}>
              {error && <Alert variant="danger">{error}</Alert>}

              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>{t('feedback.category', 'Category')} *</Form.Label>
                    <Form.Select
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>{t('feedback.priority', 'Priority')} *</Form.Label>
                    <Form.Select
                      value={formData.priority}
                      onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    >
                      {PRIORITIES.map((pri) => (
                        <option key={pri.value} value={pri.value}>
                          {pri.label}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              <Form.Group className="mb-3">
                <Form.Label>{t('feedback.title', 'Title')} *</Form.Label>
                <Form.Control
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder={t('feedback.titlePlaceholder', 'Brief summary of your feedback')}
                  required
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label>{t('feedback.description', 'Description')}</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder={t('feedback.descriptionPlaceholder', 'Detailed description of your feedback')}
                />
              </Form.Group>

              <Button
                variant="primary"
                type="submit"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending
                  ? t('common.saving', 'Saving...')
                  : t('feedback.submit', 'Submit Feedback')}
              </Button>
            </Form>
          </Card.Body>
        </Card>
      )}

      <CrudTable
        data={feedback}
        columns={columns}
        isLoading={isLoading}
        searchPlaceholder={t('common.search', 'Search feedback...')}
        pageSize={10}
      />
    </div>
  )
}
