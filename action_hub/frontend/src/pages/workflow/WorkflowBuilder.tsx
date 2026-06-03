import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, Card, Col, Form, Row, Spinner, Alert } from 'react-bootstrap'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import api from '../../lib/api'
import { t } from '../../lib/i18n'
import NodePalette from '../../components/workflow/NodePalette'
import NodeEditor from '../../components/workflow/NodeEditor'
import {
  NODE_TYPE_DEFINITIONS,
  canConnectWorkflowNodes,
  createStepKey,
  getNodeTypeDefinition,
  toReactFlowGraph,
  toWorkflowGraph,
  validateFlowGraph,
  workflowNodeTypes,
  type StepNodeData,
  type WorkflowBinding,
  type WorkflowGraph,
} from '../../components/workflow/WorkflowFlow'

interface WorkflowTemplate {
  id: number
  name_en: string
  name_cn: string
  type: string
  is_default: boolean
  version: number
}

interface TeamOption {
  tea_id: number
  tea_code: string
  tea_name_en: string
}

interface TopicOption {
  top_id: number
  top_name: string
}

const SURFACE_BORDER = '1px solid rgba(148, 163, 184, 0.22)'
const SURFACE_SHADOW = '0 14px 32px rgba(15, 23, 42, 0.08)'

function WorkflowCanvas({
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
  selectedNodeId,
  selectedEdgeId,
  setSelectedNodeId,
  setSelectedEdgeId,
  setEditorOpen,
  onCreateNode,
  reactFlowRef,
  onDeleteSelectedNode,
  onDeleteSelectedEdge,
}: {
  nodes: Array<Node<StepNodeData>>
  setNodes: ReturnType<typeof useNodesState<StepNodeData>>[1]
  onNodesChange: ReturnType<typeof useNodesState<StepNodeData>>[2]
  edges: Edge[]
  setEdges: ReturnType<typeof useEdgesState>[1]
  onEdgesChange: ReturnType<typeof useEdgesState>[2]
  selectedNodeId: string | null
  selectedEdgeId: string | null
  setSelectedNodeId: (value: string | null) => void
  setSelectedEdgeId: (value: string | null) => void
  setEditorOpen: (value: boolean) => void
  onCreateNode: (type: string, position: { x: number; y: number }) => void
  reactFlowRef: React.MutableRefObject<ReactFlowInstance | null>
  onDeleteSelectedNode: () => void
  onDeleteSelectedEdge: () => void
}) {
  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) || null,
    [nodes, selectedNodeId],
  )
  const selectedEdge = useMemo(
    () => edges.find((edge) => edge.id === selectedEdgeId) || null,
    [edges, selectedEdgeId],
  )

  return (
    <Card className="h-100 border-0" style={{ boxShadow: SURFACE_SHADOW, borderRadius: 18 }}>
      <Card.Header className="d-flex flex-wrap justify-content-between align-items-center gap-2 bg-white border-0 pb-2" style={{ borderTopLeftRadius: 18, borderTopRightRadius: 18 }}>
        <div>
          <div className="text-uppercase text-muted" style={{ fontSize: 10, letterSpacing: '0.12em' }}>React Flow</div>
          <div className="fw-semibold">{t('workflow.builder.canvas', 'Canvas')}</div>
          <div className="text-muted" style={{ fontSize: 12, maxWidth: 460 }}>
            {t('workflow.builder.instructionsReactFlow', 'Drag nodes from the palette, connect handles, and edit selections in the inspector.')}
          </div>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <Button variant="outline-secondary" size="sm" onClick={() => reactFlowRef.current?.fitView({ padding: 0.2 })}>
            {t('workflow.canvas.fitView', 'Fit view')}
          </Button>
          <Button variant="outline-secondary" size="sm" onClick={() => reactFlowRef.current?.zoomOut()}>
            {t('workflow.canvas.zoomOut', 'Zoom out')}
          </Button>
          <Button variant="outline-secondary" size="sm" onClick={() => reactFlowRef.current?.zoomIn()}>
            {t('workflow.canvas.zoomIn', 'Zoom in')}
          </Button>
        </div>
      </Card.Header>
      <Card.Body className="p-0 position-relative" style={{ minHeight: 680 }}>
        <div style={{ height: 680, width: '100%' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={workflowNodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onInit={(instance) => {
              reactFlowRef.current = instance
            }}
            onNodeClick={(_, node) => {
              setSelectedNodeId(String(node.id))
              setSelectedEdgeId(null)
            }}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(String(edge.id))
              setSelectedNodeId(null)
            }}
            onPaneClick={() => {
              setSelectedNodeId(null)
              setSelectedEdgeId(null)
            }}
            onDrop={(event) => {
              event.preventDefault()
              const nodeType = event.dataTransfer.getData('application/reactflow-step-type') || event.dataTransfer.getData('application/node-type')
              if (!nodeType || !reactFlowRef.current) {
                return
              }

              const position = reactFlowRef.current.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
              })
              onCreateNode(nodeType, position)
            }}
            onDragOver={(event) => {
              event.preventDefault()
              event.dataTransfer.dropEffect = 'move'
            }}
            onConnect={(connection: Connection) => {
              if (!canConnectWorkflowNodes(nodes, edges, connection)) {
                return
              }

              const nextEdge = {
                ...connection,
                id: `edge-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                type: 'smoothstep',
                markerEnd: { type: MarkerType.ArrowClosed },
                label: 'Next',
                data: {
                  label_en: 'Next',
                  label_cn: '下一步',
                  type: 'normal',
                },
              }

              setEdges((currentEdges) => addEdge(nextEdge, currentEdges))
            }}
            fitView
            deleteKeyCode={['Delete', 'Backspace']}
            defaultEdgeOptions={{
              type: 'smoothstep',
              markerEnd: { type: MarkerType.ArrowClosed },
            }}
            minZoom={0.35}
            maxZoom={1.4}
            proOptions={{ hideAttribution: true }}
            isValidConnection={(connection) => canConnectWorkflowNodes(nodes, edges, connection)}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#d7dee7" />
            <MiniMap
              nodeColor={(node) => getNodeTypeDefinition(node.data?.type).color}
              zoomable
              pannable
              style={{ background: '#f8fafc', border: SURFACE_BORDER }}
            />
            <Controls />
          </ReactFlow>
        </div>
      </Card.Body>
      <Card.Footer className="bg-white border-0 pt-0 pb-3">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div className="text-muted" style={{ fontSize: 12 }}>
            {selectedNode
              ? t('workflow.builder.selectedNode', 'Selected node: {{name}}', { name: selectedNode.data.name })
              : selectedEdge
                ? t('workflow.builder.selectedEdge', 'Selected connection')
                : t('workflow.builder.noSelection', 'No selection')}
          </div>
          <div className="d-flex gap-2">
            <Button variant="outline-primary" size="sm" disabled={!selectedNode} onClick={() => setEditorOpen(true)}>
              {t('common.edit', 'Edit')}
            </Button>
            <Button variant="outline-danger" size="sm" disabled={!selectedNode && !selectedEdge} onClick={() => (selectedNode ? onDeleteSelectedNode() : onDeleteSelectedEdge())}>
              {t('common.delete', 'Delete')}
            </Button>
          </div>
        </div>
      </Card.Footer>
    </Card>
  )
}

export default function WorkflowBuilder() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [workflowName, setWorkflowName] = useState('')
  const [workflowType, setWorkflowType] = useState<'action' | 'request'>('action')
  const [bindings, setBindings] = useState<WorkflowBinding[]>([])
  const [bindingScopeType, setBindingScopeType] = useState<'team' | 'topic'>('team')
  const [bindingScopeId, setBindingScopeId] = useState('')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Array<{ message: string; severity: 'error' | 'warning' }>>([])
  const [nodes, setNodes, onNodesChange] = useNodesState<StepNodeData>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)
  const suppressDirtyRef = useRef(false)
  const hasInitializedRef = useRef(false)

  const { data: teams = [] } = useQuery<TeamOption[]>({
    queryKey: ['workflow-builder', 'teams'],
    queryFn: async () => {
      const response = await api.get('/api/teams')
      return response.data.data as TeamOption[]
    },
  })

  const { data: topics = [] } = useQuery<TopicOption[]>({
    queryKey: ['workflow-builder', 'topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics')
      return response.data.data as TopicOption[]
    },
  })

  const selectedNode = useMemo(() => nodes.find((node) => node.id === selectedNodeId) || null, [nodes, selectedNodeId])
  const selectedEdge = useMemo(() => edges.find((edge) => edge.id === selectedEdgeId) || null, [edges, selectedEdgeId])

  const stepKeys = useMemo(() => nodes.map((node) => node.data.key), [nodes])

  const bindingOptions = useMemo(() => {
    if (bindingScopeType === 'team') {
      return teams.map((team) => ({ value: String(team.tea_id), label: `${team.tea_name_en} (${team.tea_code})` }))
    }
    return topics.map((topic) => ({ value: String(topic.top_id), label: topic.top_name }))
  }, [bindingScopeType, teams, topics])

  const loadTemplates = async () => {
    try {
      const resp = await api.get('/api/workflow/templates')
      setTemplates(resp.data || [])
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  useEffect(() => {
    loadTemplates()
  }, [])

  useEffect(() => {
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true
      return
    }
    if (suppressDirtyRef.current) {
      suppressDirtyRef.current = false
      return
    }
    setIsDirty(true)
  }, [nodes, edges, bindings, workflowName, workflowType])

  useEffect(() => {
    setValidationErrors(validateFlowGraph(nodes, edges))
  }, [nodes, edges])

  const getBindingLabel = (binding: WorkflowBinding) => {
    if (binding.scope_type === 'team') {
      const team = teams.find((item) => item.tea_id === binding.scope_id)
      return `${t('common.team', 'Team')}: ${team ? `${team.tea_name_en} (${team.tea_code})` : t('common.all', 'All')}`
    }

    const topic = topics.find((item) => item.top_id === binding.scope_id)
    return `${t('common.category', 'Category')}: ${topic?.top_name || t('common.all', 'All')}`
  }

  const handleAddBinding = () => {
    const nextBinding: WorkflowBinding = {
      scope_type: bindingScopeType,
      scope_id: bindingScopeId ? Number(bindingScopeId) : null,
    }

    const duplicate = bindings.some((binding) => binding.scope_type === nextBinding.scope_type && binding.scope_id === nextBinding.scope_id)
    if (duplicate) {
      return
    }

    setBindings((current) => [...current, nextBinding])
    setBindingScopeId('')
  }

  const handleRemoveBinding = (index: number) => {
    setBindings((current) => current.filter((_, bindingIndex) => bindingIndex !== index))
  }

  const handleCreateNode = (type: string, position: { x: number; y: number }) => {
    const existingKeys = new Set(nodes.map((node) => node.data.key))
    const stepKey = createStepKey(type, existingKeys)
    const nodeType = (NODE_TYPE_DEFINITIONS.find((item) => item.type === type) ? type : 'Task') as StepNodeData['type']
    const defaultLabel = t(`workflow.node.${nodeType.toLowerCase()}`, nodeType)

    setNodes((current) => [
      ...current,
      {
        id: stepKey,
        type: nodeType,
        position,
        data: {
          key: stepKey,
          type: nodeType,
          name: defaultLabel,
          name_cn: defaultLabel,
          fields: [],
          triggers: [],
          assignment: null,
          role: null,
        },
      },
    ])
    setSelectedNodeId(stepKey)
    setSelectedEdgeId(null)
    setEditorOpen(true)
  }

  const handleDeleteSelectedNode = () => {
    if (!selectedNode) {
      return
    }

    const attachedEdges = edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
    if (attachedEdges.length > 0 && !window.confirm(t('workflow.builder.deleteNodeConfirm', 'Delete this node and its connected edges?'))) {
      return
    }

    setEdges((currentEdges) => currentEdges.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id))
    setNodes((currentNodes) => currentNodes.filter((node) => node.id !== selectedNode.id))
    setSelectedNodeId(null)
    setEditorOpen(false)
  }

  const handleDeleteSelectedEdge = () => {
    if (!selectedEdge) {
      return
    }

    setEdges((currentEdges) => currentEdges.filter((edge) => edge.id !== selectedEdge.id))
    setSelectedEdgeId(null)
  }

  const handleLoadWorkflow = async (templateId: number) => {
    try {
      const resp = await api.get(`/api/workflow/templates/${templateId}`)
      const template = resp.data
      const canvasGraph = toReactFlowGraph(template.graph as WorkflowGraph)

      suppressDirtyRef.current = true
      setSelectedTemplateId(template.id)
      setWorkflowName(template.name_en)
      setWorkflowType(template.type)
      setNodes(canvasGraph.nodes)
      setEdges(canvasGraph.edges)
      setBindings(canvasGraph.bindings)
      setSelectedNodeId(null)
      setSelectedEdgeId(null)
      setEditorOpen(false)
      setIsDirty(false)
      setSaveError('')

      window.setTimeout(() => reactFlowRef.current?.fitView({ padding: 0.2 }), 0)
    } catch (error: any) {
      setSaveError(error?.response?.data?.error || error?.message || t('workflow.builder.loadFailed', 'Failed to load workflow'))
    }
  }

  const handleSaveWorkflow = async () => {
    if (!workflowName.trim()) {
      setSaveError(t('workflow.builder.nameRequired', 'Please enter a workflow name'))
      return
    }

    const graph = toWorkflowGraph(nodes, edges, workflowType === 'action' ? bindings : [])
    if (validationErrors.some((error) => error.severity === 'error')) {
      setSaveError(t('workflow.builder.validationFailed', 'Please fix validation errors before saving'))
      return
    }

    setIsSaving(true)
    setSaveError('')
    try {
      if (selectedTemplateId) {
        await api.put(`/api/workflow/templates/${selectedTemplateId}`, { graph })
      } else {
        const resp = await api.post('/api/workflow/templates', {
          name_en: workflowName,
          name_cn: workflowName,
          desc: '',
          type: workflowType,
          graph,
        })
        setSelectedTemplateId(resp.data.id)
      }

      suppressDirtyRef.current = true
      setIsDirty(false)
      await loadTemplates()
    } catch (error: any) {
      setSaveError(error?.response?.data?.error || error?.message || t('workflow.builder.saveFailed', 'Failed to save workflow'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleClearCanvas = () => {
    if (!window.confirm(t('workflow.builder.clearConfirm', 'Clear all nodes and connections?'))) {
      return
    }

    suppressDirtyRef.current = true
    setNodes([])
    setEdges([])
    setBindings([])
    setSelectedTemplateId(null)
    setWorkflowName('')
    setWorkflowType('action')
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
    setEditorOpen(false)
    setIsDirty(false)
    setSaveError('')
  }

  const handleSaveNode = (updatedNode: any) => {
    if (!selectedNode) {
      return
    }

    const nextNodeId = String(updatedNode?.id || selectedNode.id)
    setNodes((currentNodes) => currentNodes.map((node) => {
      if (node.id !== nextNodeId) {
        return node
      }

      return {
        ...node,
        id: nextNodeId,
        type: (updatedNode?.data?.type || node.type || 'Task') as StepNodeData['type'],
        data: {
          ...(node.data || {}),
          ...(updatedNode?.data || {}),
          key: nextNodeId,
          name: updatedNode?.name?.trim() || updatedNode?.data?.name || node.data.name,
          name_cn: updatedNode?.data?.name_cn || updatedNode?.name?.trim() || node.data.name_cn,
        },
      }
    }))

    setEditorOpen(false)
    setSelectedNodeId(null)
  }

  const handleLoadTemplateSelect = (value: string) => {
    const id = parseInt(value, 10)
    if (Number.isFinite(id) && id > 0) {
      void handleLoadWorkflow(id)
    }
  }

  return (
    <div>
      <div className="mb-4 d-flex flex-wrap justify-content-between align-items-end gap-3">
        <div>
          <div className="text-uppercase text-muted" style={{ fontSize: 11, letterSpacing: '0.12em' }}>Process design</div>
          <h2 className="mb-1">{t('workflow.builder', 'Workflow Builder')}</h2>
          <div className="text-muted" style={{ fontSize: 13, maxWidth: 760 }}>
            Design compact process templates, validate the graph in real time, and keep bindings and step configuration close at hand.
          </div>
        </div>
        <div className="d-flex flex-wrap align-items-center gap-2">
          <Badge bg={isDirty ? 'warning' : 'success'} text={isDirty ? 'dark' : 'light'}>
            {isDirty ? t('workflow.builder.unsaved', 'Unsaved changes') : t('workflow.builder.savedState', 'Saved')}
          </Badge>
          <div className="text-muted" style={{ fontSize: 12 }}>
            {nodes.length} nodes · {edges.length} links
          </div>
        </div>
      </div>

      <Card className="mb-3 border-0" style={{ boxShadow: SURFACE_SHADOW, borderRadius: 18 }}>
        <Card.Body className="pb-3">
          <Alert variant="light" className="mb-3">
            <div className="fw-semibold mb-1">{t('workflow.builder.quickGuide', 'Quick guide')}</div>
            <div className="small text-muted">
              {t('workflow.builder.quickGuideText', '1. Name the workflow. 2. Drag step types from the palette. 3. Connect the side handles to define flow. 4. Select a node to edit details in the inspector. 5. Save when validation is clean.')}
            </div>
          </Alert>
          <Row className="g-3 align-items-end">
            <Col xl={4} lg={5}>
              <Form.Group>
                <Form.Label>{t('workflow.builder.name', 'Workflow Name')}</Form.Label>
                <Form.Control
                  type="text"
                  value={workflowName}
                  onChange={(event) => setWorkflowName(event.target.value)}
                  placeholder={t('workflow.builder.namePlaceholder', 'Enter workflow name')}
                />
              </Form.Group>
            </Col>
            <Col xl={2} lg={3} md={4}>
              <Form.Group>
                <Form.Label>{t('workflow.builder.type', 'Type')}</Form.Label>
                <Form.Select value={workflowType} onChange={(event) => setWorkflowType(event.target.value as 'action' | 'request')}>
                  <option value="action">{t('workflow.builder.typeAction', 'Action')}</option>
                  <option value="request">{t('workflow.builder.typeRequest', 'Request')}</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col xl={3} lg={4} md={5}>
              <Form.Group>
                <Form.Label>{t('workflow.builder.loadTemplate', 'Load Template')}</Form.Label>
                <Form.Select value={selectedTemplateId || ''} onChange={(event) => handleLoadTemplateSelect(event.target.value)}>
                  <option value="">{t('workflow.builder.selectTemplate', '-- Select --')}</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name_en} (v{template.version}){template.is_default ? ' *' : ''}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col xl={3} lg={12}>
              <div className="d-flex flex-wrap gap-2 justify-content-xl-end">
                <Button size="sm" variant="primary" onClick={() => void handleSaveWorkflow()} disabled={isSaving}>
                  {isSaving ? t('common.saving', 'Saving...') : t('workflow.builder.save', 'Save')}
                </Button>
                <Button size="sm" variant="outline-secondary" onClick={handleClearCanvas}>
                  {t('workflow.builder.clear', 'Clear')}
                </Button>
              </div>
            </Col>
          </Row>

          {saveError && (
            <Alert className="mt-3 mb-0" variant="danger">
              {saveError}
            </Alert>
          )}
        </Card.Body>
      </Card>

      <Row className="g-3 align-items-stretch">
        <Col lg={3}>
          <Card className="h-100 border-0" style={{ boxShadow: SURFACE_SHADOW, borderRadius: 18 }}>
            <Card.Header className="bg-white border-0 pb-1">
              <div className="text-uppercase text-muted" style={{ fontSize: 10, letterSpacing: '0.12em' }}>Build</div>
              <div className="fw-semibold">{t('workflow.palette', 'Palette')}</div>
            </Card.Header>
            <Card.Body>
              <NodePalette />
              <div className="mt-2 text-muted" style={{ fontSize: 12 }}>
                {t('workflow.canvas.legend', 'Drag a node to the canvas. Connect handles to create transitions.')}
              </div>
              <div className="mt-3 rounded-3 p-3" style={{ border: SURFACE_BORDER, background: '#f8fafc' }}>
                <div className="fw-semibold mb-2" style={{ fontSize: 13 }}>{t('workflow.builder.nodeHelp', 'What the icons mean')}</div>
                <div className="d-grid gap-2">
                  {NODE_TYPE_DEFINITIONS.map((node) => (
                    <div key={`help-${node.type}`} className="d-flex gap-2 align-items-start" style={{ fontSize: 12 }}>
                      <span title={node.description} style={{ width: 18, textAlign: 'center' }}>{node.icon}</span>
                      <div>
                        <strong>{t(`workflow.node.${node.type.toLowerCase()}`, node.label)}</strong>
                        <div className="text-muted">{node.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {workflowType === 'action' && (
                <>
                  <div className="mt-4 pt-3" style={{ borderTop: SURFACE_BORDER }}>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h6 className="mb-0">{t('workflow.bindings', 'Bindings')}</h6>
                      <Badge bg="light" text="dark">{bindings.length}</Badge>
                    </div>
                  <Form.Group className="mb-2">
                    <Form.Label>{t('common.type', 'Type')}</Form.Label>
                    <Form.Select size="sm" value={bindingScopeType} onChange={(event) => setBindingScopeType(event.target.value as 'team' | 'topic')}>
                      <option value="team">{t('common.team', 'Team')}</option>
                      <option value="topic">{t('common.category', 'Category')}</option>
                    </Form.Select>
                  </Form.Group>
                  <Form.Group className="mb-2">
                    <Form.Label>{bindingScopeType === 'team' ? t('common.team', 'Team') : t('common.category', 'Category')}</Form.Label>
                    <Form.Select size="sm" value={bindingScopeId} onChange={(event) => setBindingScopeId(event.target.value)}>
                      <option value="">{t('common.all', 'All')}</option>
                      {bindingOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                  <Button variant="outline-primary" size="sm" onClick={handleAddBinding} className="mb-3 w-100">
                    {t('common.add', 'Add')}
                  </Button>
                  <div className="d-grid gap-2">
                    {bindings.length === 0 ? (
                      <div className="text-muted" style={{ fontSize: 12 }}>{t('workflow.noBindings', 'No bindings configured yet.')}</div>
                    ) : bindings.map((binding, index) => (
                      <div key={`${binding.scope_type}-${binding.scope_id ?? 'all'}-${index}`} className="rounded-3 p-2 d-flex justify-content-between align-items-center gap-2" style={{ border: SURFACE_BORDER, background: '#f8fafc' }}>
                        <div style={{ fontSize: 12 }}>{getBindingLabel(binding)}</div>
                        <Button variant="outline-danger" size="sm" onClick={() => handleRemoveBinding(index)}>
                          {t('common.delete', 'Delete')}
                        </Button>
                      </div>
                    ))}
                  </div>
                  </div>
                </>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={6}>
          <WorkflowCanvas
            nodes={nodes}
            setNodes={setNodes}
            onNodesChange={onNodesChange}
            edges={edges}
            setEdges={setEdges}
            onEdgesChange={onEdgesChange}
            selectedNodeId={selectedNodeId}
            selectedEdgeId={selectedEdgeId}
            setSelectedNodeId={setSelectedNodeId}
            setSelectedEdgeId={setSelectedEdgeId}
            setEditorOpen={setEditorOpen}
            onCreateNode={handleCreateNode}
            reactFlowRef={reactFlowRef}
            onDeleteSelectedNode={handleDeleteSelectedNode}
            onDeleteSelectedEdge={handleDeleteSelectedEdge}
          />

          {validationErrors.length > 0 && (
            <Card className="mt-3 border-0" style={{ boxShadow: SURFACE_SHADOW, borderRadius: 18 }}>
              <Card.Header className="fw-semibold bg-white border-0 pb-1">{t('workflow.validation', 'Validation')}</Card.Header>
              <Card.Body>
                <div className="d-grid gap-2">
                  {validationErrors.map((error, index) => (
                    <div
                      key={`${error.message}-${index}`}
                      className="rounded-3 px-3 py-2"
                      style={{
                        background: error.severity === 'error' ? '#fef2f2' : '#fff7ed',
                        color: error.severity === 'error' ? '#991b1b' : '#9a3412',
                        fontSize: 12,
                        border: `1px solid ${error.severity === 'error' ? 'rgba(239, 68, 68, 0.18)' : 'rgba(249, 115, 22, 0.18)'}`,
                      }}
                    >
                      <strong style={{ marginRight: 8 }}>{error.severity === 'error' ? 'Error' : 'Warning'}</strong>
                      {error.message}
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}
        </Col>

        <Col lg={3}>
          <Card className="h-100 border-0" style={{ boxShadow: SURFACE_SHADOW, borderRadius: 18 }}>
            <Card.Header className="bg-white border-0 pb-1">
              <div className="text-uppercase text-muted" style={{ fontSize: 10, letterSpacing: '0.12em' }}>Inspect</div>
              <div className="fw-semibold">{t('workflow.inspector', 'Inspector')}</div>
            </Card.Header>
            <Card.Body>
              {selectedNode ? (
                <>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.node.type', 'Type')}</div>
                    <div className="fw-semibold">{selectedNode.data.type}</div>
                  </div>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.node.name', 'Name')}</div>
                    <div>{selectedNode.data.name}</div>
                  </div>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.node.key', 'Key')}</div>
                    <div className="font-monospace small">{selectedNode.data.key}</div>
                  </div>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.node.details', 'Details')}</div>
                    <div className="small text-muted">
                      {selectedNode.data.sla_hours ? `SLA ${selectedNode.data.sla_hours}h` : t('workflow.node.noSla', 'No SLA configured')}
                    </div>
                  </div>
                  <div className="d-grid gap-2">
                    <Button variant="primary" onClick={() => setEditorOpen(true)}>
                      {t('common.edit', 'Edit')}
                    </Button>
                    <Button variant="outline-danger" onClick={handleDeleteSelectedNode}>
                      {t('common.delete', 'Delete')}
                    </Button>
                  </div>
                </>
              ) : selectedEdge ? (
                <>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.transition', 'Transition')}</div>
                    <div className="fw-semibold">{selectedEdge.label || t('workflow.builder.link', 'Link')}</div>
                  </div>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.source', 'Source')}</div>
                    <div className="small">{selectedEdge.source}</div>
                  </div>
                  <div className="rounded-3 p-3 mb-3" style={{ background: '#f8fafc', border: SURFACE_BORDER }}>
                    <div className="text-muted small">{t('workflow.target', 'Target')}</div>
                    <div className="small">{selectedEdge.target}</div>
                  </div>
                  <div className="d-grid">
                    <Button variant="outline-danger" onClick={handleDeleteSelectedEdge}>
                      {t('common.delete', 'Delete')}
                    </Button>
                  </div>
                </>
              ) : (
                <div className="rounded-3 p-3 text-muted" style={{ background: '#f8fafc', border: SURFACE_BORDER, fontSize: 13 }}>
                  {t('workflow.noSelection', 'Select a node or connection to inspect it.')}
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <NodeEditor
        show={editorOpen}
        node={selectedNode}
        availableStepKeys={stepKeys.filter((key) => key !== selectedNode?.data.key)}
        onClose={() => setEditorOpen(false)}
        onSave={handleSaveNode}
      />
    </div>
  )
}
