/**
 * WF-22: Workflow Workbench Panel Component
 * 
 * Displays the complete workflow workbench for an active workflow instance.
 * Includes: step cards, form fields, attachments, and timeline.
 */

import { useState } from 'react'
import { Badge, Button, Card, Col, Form, Row, Spinner, Alert, Table } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { t } from '../../lib/i18n'
import api from '../../lib/api'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

interface WorkbenchData {
  workflow_summary: {
    id: number
    template_id: number
    template_name: string
    template_name_cn?: string
    type: string
    status: string
    outcome?: string | null
    started_at: string
    completed_at?: string | null
    action?: {
      act_id: number
      act_title: string
      act_status: string
      act_priority?: string
    } | null
  }
  current_steps: Array<{
    step_id: number
    step_key: string
    step_name: string
    step_type: string
    status: string
    assignee?: string | null
    entered_at: string
    accepted_at?: string | null
    sla_deadline?: string | null
    comment?: string | null
  }>
  field_definitions: Array<{
    step_key: string
    step_id: number
    key: string
    type: string
    label_en: string
    label_cn?: string
    required?: boolean
    options?: string[]
  }>
  field_values: Record<number, Record<string, any>>
  attachments: Array<{
    id: number
    filename: string
    size_bytes: number
    mime_type: string
    uploaded_by: number
    uploaded_by_name: string
    uploaded_at: string
    description?: string | null
  }>
  timeline: Array<{
    step_id: number
    step_key: string
    step_name: string
    step_type: string
    status: string
    assignee?: string | null
    entered_at: string
    accepted_at?: string | null
    completed_at?: string | null
    comment?: string | null
  }>
  eligible_users: Array<{
    usr_id: number
    usr_display_name: string
    usr_display_name_cn?: string
    usr_email: string
    usr_team_id: number
    team_name?: string
  }>
}

interface WorkbenchPanelProps {
  instanceId: number
  actionId?: number
}

export default function WorkbenchPanel({ instanceId, actionId }: WorkbenchPanelProps) {
  const [feedback, setFeedback] = useState<{ variant: 'success' | 'danger'; text: string } | null>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [comment, setComment] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileDescription, setFileDescription] = useState('')
  const queryClient = useQueryClient()

  // Fetch workbench data
  const { data: workbench, isLoading, error, refetch } = useQuery<WorkbenchData>({
    queryKey: ['workflow', 'workbench', instanceId],
    queryFn: async () => {
      const response = await api.get(`/api/workflow/instances/${instanceId}/workbench`)
      return response.data.data as WorkbenchData
    },
    enabled: !!instanceId,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const acceptStepMutation = useMutation({
    mutationFn: async (stepId: number) => {
      const response = await api.post(`/api/workflow/steps/${stepId}/accept`, {
        comment: comment || undefined,
      })
      return response.data
    },
    onSuccess: () => {
      setFeedback({ variant: 'success', text: t('workflow.stepAccepted', 'Step accepted successfully') })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'workbench', instanceId] })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'my-steps'] })
      setComment('')
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (error: any) => {
      setFeedback({ variant: 'danger', text: error.response?.data?.error || t('common.error', 'Failed to accept step') })
      setTimeout(() => setFeedback(null), 5000)
    },
  })

  // Save draft mutation
  const saveDraftMutation = useMutation({
    mutationFn: async (stepId: number) => {
      const fields = Object.entries(formData).map(([key, value]) => ({ key, value }))
      const response = await api.post(`/api/workflow/steps/${stepId}/draft`, {
        fields,
        comment: comment || undefined,
      })
      return response.data
    },
    onSuccess: () => {
      setFeedback({ variant: 'success', text: t('workflow.draftSaved', 'Draft saved successfully') })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'workbench', instanceId] })
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (error: any) => {
      setFeedback({ variant: 'danger', text: error.response?.data?.error || t('common.error', 'Failed to save draft') })
      setTimeout(() => setFeedback(null), 5000)
    },
  })

  // Upload attachment mutation
  const uploadAttachmentMutation = useMutation({
    mutationFn: async ({ stepId, file, description }: { stepId: number; file: File; description?: string }) => {
      const formDataUpload = new FormData()
      formDataUpload.append('file', file)
      if (description) {
        formDataUpload.append('description', description)
      }
      const response = await api.post(`/api/workflow/steps/${stepId}/attachments`, formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: () => {
      setFeedback({ variant: 'success', text: t('workflow.attachmentUploaded', 'Attachment uploaded successfully') })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'workbench', instanceId] })
      setSelectedFile(null)
      setFileDescription('')
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (error: any) => {
      setFeedback({ 
        variant: 'danger', 
        text: error.response?.data?.error || t('workflow.uploadFailed', 'Failed to upload attachment') 
      })
      setTimeout(() => setFeedback(null), 5000)
    },
  })

  // Delete attachment mutation
  const deleteAttachmentMutation = useMutation({
    mutationFn: async ({ stepId, attachmentId }: { stepId: number; attachmentId: number }) => {
      const response = await api.delete(`/api/workflow/steps/${stepId}/attachments/${attachmentId}`)
      return response.data
    },
    onSuccess: () => {
      setFeedback({ variant: 'success', text: t('workflow.attachmentDeleted', 'Attachment deleted successfully') })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'workbench', instanceId] })
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (error: any) => {
      setFeedback({ variant: 'danger', text: error.response?.data?.error || t('common.error', 'Failed to delete attachment') })
      setTimeout(() => setFeedback(null), 5000)
    },
  })

  // Download attachment
  const handleDownload = (attachmentId: number, filename: string) => {
    window.open(`/api/workflow/attachments/${attachmentId}/download`, '_blank')
  }

  // Handle field change
  const handleFieldChange = (fieldKey: string, value: any) => {
    setFormData(prev => ({ ...prev, [fieldKey]: value }))
  }

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  // Get status badge variant
  const getStatusVariant = (status: string): string => {
    const variants: Record<string, string> = {
      'Pending': 'warning',
      'Accepted': 'info',
      'Completed': 'success',
      'Rejected': 'danger',
      'Paused': 'secondary',
      'Skipped': 'light',
      'Delegated': 'primary',
      'WaitingForChild': 'info',
    }
    return variants[status] || 'secondary'
  }

  if (isLoading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" variant="primary" />
        <div className="mt-2 text-muted">{t('workflow.loadingWorkbench', 'Loading workbench...')}</div>
      </div>
    )
  }

  if (error || !workbench) {
    return (
      <Alert variant="danger">
        {t('workflow.loadError', 'Failed to load workbench data')}
      </Alert>
    )
  }

  const { workflow_summary, current_steps, field_definitions, field_values, attachments, timeline, eligible_users } = workbench

  // Get first active step for form display
  const activeStep = current_steps.length > 0 ? current_steps[0] : null
  const activeStepFields = activeStep ? field_definitions.filter(f => f.step_id === activeStep.step_id) : []
  const activeStepFieldValues = activeStep ? (field_values[activeStep.step_id] || {}) : {}

  return (
    <div className="workbench-panel">
      {feedback && (
        <Alert variant={feedback.variant} onClose={() => setFeedback(null)} dismissible>
          {feedback.text}
        </Alert>
      )}

      {/* Header Summary */}
      <Card className="mb-4">
        <Card.Header className="bg-light">
          <h5 className="mb-0">{t('workflow.workbench', 'Workflow Workbench')}</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <div className="mb-2">
                <strong>{t('workflow.template', 'Template')}:</strong> {workflow_summary.template_name}
              </div>
              <div className="mb-2">
                <strong>{t('common.status', 'Status')}:</strong>{' '}
                <Badge bg={getStatusVariant(workflow_summary.status)}>{workflow_summary.status}</Badge>
              </div>
              {workflow_summary.action && (
                <div className="mb-2">
                  <strong>{t('workflow.boundAction', 'Bound Action')}:</strong>{' '}
                  <Link to={`/actions/${workflow_summary.action.act_id}`}>
                    {workflow_summary.action.act_title}
                  </Link>
                </div>
              )}
            </Col>
            <Col md={6}>
              <div className="mb-2">
                <strong>{t('workflow.startedAt', 'Started At')}:</strong> {formatChinaDateTimeNoSeconds(workflow_summary.started_at)}
              </div>
              {workflow_summary.completed_at && (
                <div className="mb-2">
                  <strong>{t('workflow.completedAt', 'Completed At')}:</strong> {formatChinaDateTimeNoSeconds(workflow_summary.completed_at)}
                </div>
              )}
              {workflow_summary.outcome && (
                <div className="mb-2">
                  <strong>{t('workflow.outcome', 'Outcome')}:</strong> {workflow_summary.outcome}
                </div>
              )}
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Current Step Card */}
      {activeStep && (
        <Card className="mb-4">
          <Card.Header className="bg-primary text-white">
            <h6 className="mb-0">
              {activeStep.step_name} - <Badge bg="light" text="dark">{activeStep.status}</Badge>
            </h6>
          </Card.Header>
          <Card.Body>
            <Row className="mb-3">
              <Col md={4}>
                <strong>{t('workflow.assignee', 'Assignee')}:</strong> {activeStep.assignee || t('common.unassigned', 'Unassigned')}
              </Col>
              <Col md={4}>
                <strong>{t('workflow.enteredAt', 'Entered At')}:</strong> {formatChinaDateTimeNoSeconds(activeStep.entered_at)}
              </Col>
              {activeStep.accepted_at && (
                <Col md={4}>
                  <strong>{t('workflow.acceptedAt', 'Accepted At')}:</strong> {formatChinaDateTimeNoSeconds(activeStep.accepted_at)}
                </Col>
              )}
              {activeStep.sla_deadline && (
                <Col md={4}>
                  <strong>{t('workflow.slaDeadline', 'SLA Deadline')}:</strong> {formatChinaDateTimeNoSeconds(activeStep.sla_deadline)}
                </Col>
              )}
            </Row>

            {/* Step Form Fields */}
            {activeStepFields.length > 0 && (
              <Form>
                <Row>
                  {activeStepFields.map((field) => {
                    const value = activeStepFieldValues[field.key] ?? formData[field.key] ?? ''
                    return (
                      <Col md={6} key={field.key}>
                        <Form.Group className="mb-3">
                          <Form.Label>
                            {field.label_en} {field.required && <span className="text-danger">*</span>}
                          </Form.Label>
                          {field.type === 'text' && (
                            <Form.Control
                              type="text"
                              value={value}
                              onChange={(e) => handleFieldChange(field.key, e.target.value)}
                              isInvalid={field.required && !value}
                            />
                          )}
                          {field.type === 'number' && (
                            <Form.Control
                              type="number"
                              value={value}
                              onChange={(e) => handleFieldChange(field.key, parseFloat(e.target.value) || '')}
                              isInvalid={field.required && !value}
                            />
                          )}
                          {field.type === 'date' && (
                            <Form.Control
                              type="date"
                              value={value}
                              onChange={(e) => handleFieldChange(field.key, e.target.value)}
                              isInvalid={field.required && !value}
                            />
                          )}
                          {field.type === 'dropdown' && field.options && (
                            <Form.Select
                              value={value}
                              onChange={(e) => handleFieldChange(field.key, e.target.value)}
                              isInvalid={field.required && !value}
                            >
                              <option value="">{t('common.select', 'Select...')}</option>
                              {field.options.map((opt: string) => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </Form.Select>
                          )}
                          {field.type === 'checkbox' && (
                            <Form.Check
                              type="checkbox"
                              checked={value === true || value === 'true'}
                              onChange={(e) => handleFieldChange(field.key, e.target.checked)}
                              label={field.label_en}
                            />
                          )}
                          {field.type === 'checklist' && field.options && (
                            <div>
                              {field.options.map((opt: string) => (
                                <Form.Check
                                  key={opt}
                                  type="checkbox"
                                  label={opt}
                                  checked={(Array.isArray(value) ? value : []).includes(opt)}
                                  onChange={(e) => {
                                    const current = Array.isArray(value) ? value : []
                                    const updated = e.target.checked
                                      ? [...current, opt]
                                      : current.filter((v: string) => v !== opt)
                                    handleFieldChange(field.key, updated)
                                  }}
                                />
                              ))}
                            </div>
                          )}
                        </Form.Group>
                      </Col>
                    )
                  })}
                </Row>
              </Form>
            )}

            {activeStepFields.length === 0 && (
              <Alert variant="info">
                {t('workflow.noFields', 'No editable fields for this step')}
              </Alert>
            )}

            <Form.Group className="mb-3">
              <Form.Label>{t('common.comment', 'Comment')}</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={t('workflow.progressNote', 'Progress note (optional)')}
              />
            </Form.Group>

            <div className="d-flex gap-2 flex-wrap">
              {activeStep.status === 'Pending' && (
                <Button
                  variant="success"
                  onClick={() => acceptStepMutation.mutate(activeStep.step_id)}
                  disabled={acceptStepMutation.isPending}
                >
                  {acceptStepMutation.isPending && <Spinner animation="border" size="sm" className="me-2" />}
                  {t('workflow.acceptStep', 'Accept')}
                </Button>
              )}
              <Button
                variant="primary"
                onClick={() => activeStep && saveDraftMutation.mutate(activeStep.step_id)}
                disabled={saveDraftMutation.isPending}
              >
                {saveDraftMutation.isPending && <Spinner animation="border" size="sm" className="me-2" />}
                {t('workflow.saveDraft', 'Save Draft')}
              </Button>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Attachments Panel */}
      <Card className="mb-4">
        <Card.Header className="bg-light">
          <h6 className="mb-0">{t('workflow.attachments', 'Attachments')}</h6>
        </Card.Header>
        <Card.Body>
          {/* Upload Form */}
          {activeStep && (
            <Form className="mb-3">
              <Row>
                <Col md={6}>
                  <Form.Control
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    accept=".pdf,.docx,.xlsx,.pptx,.csv,.txt,.png,.jpg,.jpeg"
                  />
                  <Form.Text className="text-muted">
                    {t('workflow.allowedTypes', 'Allowed: pdf, docx, xlsx, pptx, csv, txt, png, jpg (max 25MB)')}
                  </Form.Text>
                </Col>
                <Col md={4}>
                  <Form.Control
                    type="text"
                    placeholder={t('workflow.description', 'Description (optional)')}
                    value={fileDescription}
                    onChange={(e) => setFileDescription(e.target.value)}
                  />
                </Col>
                <Col md={2}>
                  <Button
                    variant="outline-primary"
                    onClick={() => {
                      if (selectedFile && activeStep) {
                        uploadAttachmentMutation.mutate({
                          stepId: activeStep.step_id,
                          file: selectedFile,
                          description: fileDescription || undefined,
                        })
                      }
                    }}
                    disabled={!selectedFile || uploadAttachmentMutation.isPending}
                  >
                    {uploadAttachmentMutation.isPending ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      t('common.upload', 'Upload')
                    )}
                  </Button>
                </Col>
              </Row>
            </Form>
          )}

          {/* Attachments List */}
          {attachments.length > 0 ? (
            <Table responsive hover size="sm">
              <thead>
                <tr>
                  <th>{t('workflow.filename', 'Filename')}</th>
                  <th>{t('workflow.size', 'Size')}</th>
                  <th>{t('workflow.uploadedBy', 'Uploaded By')}</th>
                  <th>{t('workflow.uploadedAt', 'Uploaded At')}</th>
                  <th>{t('common.actions', 'Actions')}</th>
                </tr>
              </thead>
              <tbody>
                {attachments.map((att) => (
                  <tr key={att.id}>
                    <td>
                      <div>
                        <a href="#" onClick={(e) => { e.preventDefault(); handleDownload(att.id, att.filename) }}>
                          {att.filename}
                        </a>
                        {att.description && (
                          <div className="small text-muted">{att.description}</div>
                        )}
                      </div>
                    </td>
                    <td>{formatFileSize(att.size_bytes)}</td>
                    <td>{att.uploaded_by_name}</td>
                    <td>{formatChinaDateTimeNoSeconds(att.uploaded_at)}</td>
                    <td>
                      <Button
                        size="sm"
                        variant="outline-danger"
                        onClick={() => activeStep && deleteAttachmentMutation.mutate({ 
                          stepId: activeStep.step_id, 
                          attachmentId: att.id 
                        })}
                      >
                        {t('common.delete', 'Delete')}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <Alert variant="light" className="mb-0">
              {t('workflow.noAttachments', 'No attachments yet')}
            </Alert>
          )}
        </Card.Body>
      </Card>

      {/* Timeline */}
      <Card>
        <Card.Header className="bg-light">
          <h6 className="mb-0">{t('workflow.timeline', 'Timeline')}</h6>
        </Card.Header>
        <Card.Body>
          <Table responsive hover size="sm">
            <thead>
              <tr>
                <th>{t('workflow.step', 'Step')}</th>
                <th>{t('common.status', 'Status')}</th>
                <th>{t('workflow.assignee', 'Assignee')}</th>
                <th>{t('workflow.enteredAt', 'Entered')}</th>
                <th>{t('workflow.completedAt', 'Completed')}</th>
                <th>{t('common.comment', 'Comment')}</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((entry) => (
                <tr key={entry.step_id}>
                  <td>
                    <strong>{entry.step_name}</strong>
                    <div className="small text-muted">{entry.step_type}</div>
                  </td>
                  <td>
                    <Badge bg={getStatusVariant(entry.status)}>{entry.status}</Badge>
                  </td>
                  <td>{entry.assignee || '-'}</td>
                  <td>{formatChinaDateTimeNoSeconds(entry.entered_at)}</td>
                  <td>{formatChinaDateTimeNoSeconds(entry.completed_at)}</td>
                  <td>{entry.comment || '-'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  )
}
