import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap'
import { Link, useNavigate } from 'react-router-dom'
import KpiCard from '../../components/shared/KpiCard'
import api from '../../lib/api'
import { t } from '../../lib/i18n'
import { formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

interface WorkflowStepItem {
  step_id: number
  step_key: string
  status: string
  entered_at: string | null
  sla_deadline: string | null
  instance_id: number
  action_id: number | null
  action_title: string | null
  workflow_name: string
}

interface ActiveTemplateCount {
  template_id: number
  name_en: string
  active_count: number
}

interface BottleneckItem {
  step_key: string
  template_name: string
  count: number
  oldest_hours: number
}

interface CompletionItem {
  template_id: number
  name_en: string
  total: number
  completed: number
  rate: number
}

interface SlaSummary {
  total: number
  on_time: number
  compliance_pct: number
}

interface WorkflowTemplateSummary {
  id: number
  name_en: string
  type: string
  version: number
}

interface WorkflowTemplateDetail {
  id: number
  name_en: string
  type: string
  graph: {
    steps?: Record<string, any>
    transitions?: Array<{ from: string; to: string }>
  }
}

function formatDateTime(value: string | null | undefined) {
  return formatChinaDateTimeNoSeconds(value)
}

export default function WorkflowDashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [requestTitle, setRequestTitle] = useState('')
  const [requestDescription, setRequestDescription] = useState('')
  const [requestFields, setRequestFields] = useState<Record<string, any>>({})

  const { data: mySteps = [], isLoading: loadingMySteps } = useQuery<WorkflowStepItem[]>({
    queryKey: ['workflow', 'my-steps'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/my-steps')
      return response.data as WorkflowStepItem[]
    },
  })

  const { data: activeCounts = [], isLoading: loadingActiveCounts } = useQuery<ActiveTemplateCount[]>({
    queryKey: ['workflow', 'dashboard', 'active'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/dashboard/active')
      return response.data as ActiveTemplateCount[]
    },
  })

  const { data: bottlenecks = [], isLoading: loadingBottlenecks } = useQuery<BottleneckItem[]>({
    queryKey: ['workflow', 'dashboard', 'bottlenecks'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/dashboard/bottlenecks', { params: { limit: 5 } })
      return response.data as BottleneckItem[]
    },
  })

  const { data: completion = [], isLoading: loadingCompletion } = useQuery<CompletionItem[]>({
    queryKey: ['workflow', 'dashboard', 'completion'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/dashboard/completion')
      return response.data as CompletionItem[]
    },
  })

  const { data: sla, isLoading: loadingSla } = useQuery<SlaSummary>({
    queryKey: ['workflow', 'dashboard', 'sla'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/dashboard/sla')
      return response.data as SlaSummary
    },
  })

  const isLoading = loadingMySteps || loadingActiveCounts || loadingBottlenecks || loadingCompletion || loadingSla
  const totalActiveInstances = activeCounts.reduce((sum, item) => sum + item.active_count, 0)
  const totalTemplates = activeCounts.length

  const { data: requestTemplates = [] } = useQuery<WorkflowTemplateSummary[]>({
    queryKey: ['workflow', 'request-templates'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/templates', { params: { type: 'request' } })
      return response.data as WorkflowTemplateSummary[]
    },
  })

  const { data: selectedTemplate } = useQuery<WorkflowTemplateDetail>({
    queryKey: ['workflow', 'template', selectedTemplateId],
    queryFn: async () => {
      const response = await api.get(`/api/workflow/templates/${selectedTemplateId}`)
      return response.data as WorkflowTemplateDetail
    },
    enabled: Boolean(selectedTemplateId),
  })

  const launchRequestMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/api/workflow/requests', {
        template_id: Number(selectedTemplateId),
        title: requestTitle,
        description: requestDescription,
        fields: requestFields,
      })
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflow', 'my-steps'] })
      queryClient.invalidateQueries({ queryKey: ['workflow', 'dashboard', 'active'] })
      setRequestTitle('')
      setRequestDescription('')
      setRequestFields({})
      navigate(`/workflow/workbench/${data.instance_id}`)
    },
  })

  const startStepFields = useMemo(() => {
    const graph = selectedTemplate?.graph
    if (!graph?.steps) {
      return []
    }

    const incoming = new Set((graph.transitions || []).map((transition) => transition.to))
    const startEntry = Object.entries(graph.steps).find(([stepKey]) => !incoming.has(stepKey))
    if (!startEntry) {
      return []
    }

    const [, stepDef] = startEntry
    return Array.isArray(stepDef.fields) ? stepDef.fields : []
  }, [selectedTemplate])

  const selectedTemplateSummary = useMemo(
    () => requestTemplates.find((template) => String(template.id) === selectedTemplateId) || null,
    [requestTemplates, selectedTemplateId],
  )

  const hasSelectedTemplate = Boolean(selectedTemplateId)

  const renderInitialField = (field: any) => {
    const value = requestFields[field.key]
    if (field.type === 'dropdown') {
      return (
        <Form.Select value={value || ''} onChange={(event) => setRequestFields((current) => ({ ...current, [field.key]: event.target.value }))}>
          <option value="">{t('workflow.selectOption', 'Select')}</option>
          {(field.options || []).map((option: string) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </Form.Select>
      )
    }

    if (field.type === 'checkbox') {
      return (
        <Form.Check
          type="switch"
          checked={Boolean(value)}
          onChange={(event) => setRequestFields((current) => ({ ...current, [field.key]: event.target.checked }))}
        />
      )
    }

    if (field.type === 'checklist') {
      const selectedValues = Array.isArray(value) ? value : []
      return (
        <div>
          {(field.options || []).map((option: string) => (
            <Form.Check
              key={option}
              type="checkbox"
              label={option}
              checked={selectedValues.includes(option)}
              onChange={(event) => {
                setRequestFields((current) => {
                  const existing = Array.isArray(current[field.key]) ? current[field.key] : []
                  const nextValues = event.target.checked
                    ? [...existing, option]
                    : existing.filter((item: string) => item !== option)
                  return { ...current, [field.key]: nextValues }
                })
              }}
            />
          ))}
        </div>
      )
    }

    return (
      <Form.Control
        type={field.type === 'date' ? 'date' : field.type === 'number' ? 'number' : 'text'}
        value={value || ''}
        onChange={(event) => setRequestFields((current) => ({
          ...current,
          [field.key]: field.type === 'number' ? event.target.value : event.target.value,
        }))}
      />
    )
  }

  return (
    <div>
      <h2 className="mb-4">{t('workflow.dashboard', 'Workflow Dashboard')}</h2>

      {isLoading && (
        <div className="d-flex justify-content-center py-5">
          <Spinner animation="border" />
        </div>
      )}

      {!isLoading && (
        <>
          <Alert variant="light" className="mb-4">
            <div className="fw-semibold mb-1">{t('workflow.dashboard.quickGuide', 'Workflow quick guide')}</div>
            <div className="small text-muted">
              {t('workflow.dashboard.quickGuideText', 'Use this page to start request workflows, see the steps currently waiting for you, and open the workbench for action. The workflow area is the primary place to manage process workflows.')}
            </div>
          </Alert>

          <Row className="mb-4 g-3">
            <Col md={3}>
              <KpiCard title={t('workflow.myOpenSteps', 'My Open Steps')} value={mySteps.length} />
            </Col>
            <Col md={3}>
              <KpiCard title={t('workflow.activeInstances', 'Active Instances')} value={totalActiveInstances} />
            </Col>
            <Col md={3}>
              <KpiCard title={t('workflow.activeTemplates', 'Active Templates')} value={totalTemplates} />
            </Col>
            <Col md={3}>
              <KpiCard title={t('workflow.slaCompliance', 'SLA Compliance')} value={`${sla?.compliance_pct ?? 0}%`} subtitle={`${sla?.on_time ?? 0}/${sla?.total ?? 0}`} />
            </Col>
          </Row>

          <Row className="g-4">
            <Col lg={7}>
              <Card className="mb-4">
                <Card.Header>{t('workflow.launchRequest', 'Launch Workflow Request')}</Card.Header>
                <Card.Body>
                  {requestTemplates.length === 0 ? (
                    <Alert variant="light" className="mb-0">{t('workflow.noRequestTemplates', 'No request-type workflow templates are available yet.')}</Alert>
                  ) : (
                    <Form onSubmit={(event) => {
                      event.preventDefault()
                      launchRequestMutation.mutate()
                    }}>
                      <Form.Group className="mb-3">
                        <Form.Label>{t('workflow.template', 'Template')}</Form.Label>
                        <Form.Select value={selectedTemplateId} onChange={(event) => {
                          const nextTemplateId = event.target.value
                          const nextTemplate = requestTemplates.find((template) => String(template.id) === nextTemplateId)
                          setSelectedTemplateId(nextTemplateId)
                          setRequestFields({})
                          if (!requestTitle.trim() && nextTemplate) {
                            setRequestTitle(nextTemplate.name_en)
                          }
                        }}>
                          <option value="">{t('workflow.selectTemplate', 'Select template')}</option>
                          {requestTemplates.map((template) => (
                            <option key={template.id} value={template.id}>{template.name_en} (v{template.version})</option>
                          ))}
                        </Form.Select>
                        <Form.Text className="text-muted">
                          {t('workflow.launchTemplateHint', 'Choose the workflow first. The launch form will then show only the fields needed to start it.')}
                        </Form.Text>
                      </Form.Group>

                      {!hasSelectedTemplate ? (
                        <Alert variant="light" className="mb-0">
                          <div className="fw-semibold mb-1">{t('workflow.launchHowTo', 'How to launch')}</div>
                          <div className="small text-muted">
                            {t('workflow.launchHowToText', '1. Choose a template. 2. Give the request a clear title. 3. Fill the start questions only if they appear.')}
                          </div>
                        </Alert>
                      ) : (
                        <>
                          <Alert variant="light" className="mb-3">
                            <div className="d-flex flex-wrap gap-2 align-items-center mb-1">
                              <span className="fw-semibold">{selectedTemplateSummary?.name_en || t('workflow.selectedTemplate', 'Selected template')}</span>
                              {selectedTemplateSummary && <Badge bg="secondary">v{selectedTemplateSummary.version}</Badge>}
                              {selectedTemplateSummary?.type && <Badge bg="info">{selectedTemplateSummary.type}</Badge>}
                            </div>
                            <div className="small text-muted">
                              {startStepFields.length > 0
                                ? t('workflow.launchQuestionsHint', 'This workflow asks {{count}} launch question(s) before it starts.', { count: startStepFields.length })
                                : t('workflow.launchQuestionsNone', 'This workflow starts immediately after you enter the request title and description.')}
                            </div>
                          </Alert>

                          <Row className="g-3 mb-3">
                            <Col md={6}>
                              <Form.Group>
                                <Form.Label>{t('action.title', 'Title')}</Form.Label>
                                <Form.Control
                                  value={requestTitle}
                                  onChange={(event) => setRequestTitle(event.target.value)}
                                  minLength={5}
                                  required
                                  placeholder={t('workflow.requestTitlePlaceholder', 'Example: New supplier onboarding')}
                                />
                              </Form.Group>
                            </Col>
                            <Col md={6}>
                              <Form.Group>
                                <Form.Label>{t('common.description', 'Description')}</Form.Label>
                                <Form.Control
                                  as="textarea"
                                  rows={3}
                                  value={requestDescription}
                                  onChange={(event) => setRequestDescription(event.target.value)}
                                  placeholder={t('workflow.requestDescriptionPlaceholder', 'Add the context the first reviewer needs to act quickly.')}
                                />
                              </Form.Group>
                            </Col>
                          </Row>

                          {startStepFields.length > 0 && (
                            <>
                              <h6>{t('workflow.startForm', 'Start Step Form')}</h6>
                              <div className="small text-muted mb-3">
                                {t('workflow.startFormHint', 'Only the fields below are required at launch. The rest of the workflow happens in the workbench.')}
                              </div>
                              <Row className="g-3 mb-3">
                                {startStepFields.map((field: any) => (
                                  <Col md={6} key={field.key}>
                                    <Form.Group>
                                      <Form.Label>{field.label_en || field.key}{field.required ? ' *' : ''}</Form.Label>
                                      {renderInitialField(field)}
                                    </Form.Group>
                                  </Col>
                                ))}
                              </Row>
                            </>
                          )}
                        </>
                      )}

                      {launchRequestMutation.isError && (
                        <Alert variant="danger" className="mt-3">
                          {((launchRequestMutation.error as any)?.response?.data?.error) || t('common.error', 'Error')}
                        </Alert>
                      )}

                      <Button type="submit" disabled={!selectedTemplateId || launchRequestMutation.isPending} className="mt-3">
                        {launchRequestMutation.isPending ? t('common.saving', 'Saving...') : t('workflow.launch', 'Launch Workflow')}
                      </Button>
                    </Form>
                  )}
                </Card.Body>
              </Card>

              <Card className="mb-4">
                <Card.Header>{t('workflow.myQueue', 'My Workflow Queue')}</Card.Header>
                <Card.Body className="p-0">
                  {mySteps.length === 0 ? (
                    <Alert variant="light" className="m-3 mb-0">{t('workflow.noAssignedSteps', 'No workflow steps are currently assigned to you.')}</Alert>
                  ) : (
                    <Table responsive hover className="mb-0">
                      <thead>
                        <tr>
                          <th>{t('workflow.step', 'Step')}</th>
                          <th>{t('common.status', 'Status')}</th>
                          <th>{t('workflow.workflow', 'Workflow')}</th>
                          <th>{t('workflow.slaDeadline', 'SLA deadline')}</th>
                          <th>{t('common.actions', 'Actions')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mySteps.map((step) => (
                          <tr key={step.step_id}>
                            <td>
                              <div className="fw-semibold">{step.step_key}</div>
                              <div className="small text-muted">{step.action_title || t('workflow.standaloneRequest', 'Process request')}</div>
                            </td>
                            <td><Badge bg="primary">{step.status}</Badge></td>
                            <td>{step.workflow_name}</td>
                            <td>{formatDateTime(step.sla_deadline)}</td>
                            <td>
                              <div className="d-flex flex-column gap-1">
                                <Link to={`/workflow/workbench/${step.instance_id}`}>{t('workflow.openWorkbench', 'Open Workbench')}</Link>
                                {step.action_id && (
                                  <Link to={`/actions/${step.action_id}`}>{t('workflow.openAction', 'Open Action')}</Link>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>

              <Card>
                <Card.Header>{t('workflow.completionByTemplate', 'Completion by Template')}</Card.Header>
                <Card.Body className="p-0">
                  {completion.length === 0 ? (
                    <Alert variant="light" className="m-3 mb-0">{t('workflow.noCompletionData', 'No workflow completion data is available yet.')}</Alert>
                  ) : (
                    <Table responsive hover className="mb-0">
                      <thead>
                        <tr>
                          <th>{t('workflow.template', 'Template')}</th>
                          <th>{t('workflow.completed', 'Completed')}</th>
                          <th>{t('workflow.total', 'Total')}</th>
                          <th>{t('workflow.rate', 'Rate')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {completion.map((item) => (
                          <tr key={item.template_id}>
                            <td>{item.name_en}</td>
                            <td>{item.completed}</td>
                            <td>{item.total}</td>
                            <td>{item.rate}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            </Col>

            <Col lg={5}>
              <Card className="mb-4">
                <Card.Header>{t('workflow.activeByTemplate', 'Active by Template')}</Card.Header>
                <Card.Body className="p-0">
                  {activeCounts.length === 0 ? (
                    <Alert variant="light" className="m-3 mb-0">{t('workflow.noActiveInstances', 'There are no active workflow instances right now.')}</Alert>
                  ) : (
                    <Table responsive hover className="mb-0">
                      <thead>
                        <tr>
                          <th>{t('workflow.template', 'Template')}</th>
                          <th>{t('workflow.active', 'Active')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeCounts.map((item) => (
                          <tr key={item.template_id}>
                            <td>{item.name_en}</td>
                            <td>{item.active_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>

              <Card>
                <Card.Header>{t('workflow.bottlenecks', 'Current Bottlenecks')}</Card.Header>
                <Card.Body className="p-0">
                  {bottlenecks.length === 0 ? (
                    <Alert variant="light" className="m-3 mb-0">{t('workflow.noBottlenecks', 'No current bottlenecks were detected.')}</Alert>
                  ) : (
                    <Table responsive hover className="mb-0">
                      <thead>
                        <tr>
                          <th>{t('workflow.step', 'Step')}</th>
                          <th>{t('workflow.workflow', 'Workflow')}</th>
                          <th>{t('workflow.waiting', 'Waiting')}</th>
                          <th>{t('workflow.oldestHours', 'Oldest h')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bottlenecks.map((item, index) => (
                          <tr key={`${item.template_name}-${item.step_key}-${index}`}>
                            <td>{item.step_key}</td>
                            <td>{item.template_name}</td>
                            <td>{item.count}</td>
                            <td>{item.oldest_hours}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}