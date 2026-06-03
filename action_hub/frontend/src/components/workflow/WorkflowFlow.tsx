import { memo } from 'react'
import {
  Handle,
  MarkerType,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  Position,
} from '@xyflow/react'

export type WorkflowStepType = 'Task' | 'Approval' | 'Gateway' | 'Service' | 'Notification' | 'Timer' | 'Join' | 'End'

export interface WorkflowBinding {
  scope_type: 'team' | 'topic'
  scope_id: number | null
}

export interface WorkflowTransition {
  from: string
  to: string
  label_en?: string
  label_cn?: string
  type?: 'normal' | 'rejection' | 'timeout' | 'condition'
}

export interface WorkflowStepDefinition {
  name_en?: string
  name_cn?: string
  type?: WorkflowStepType
  order?: number
  role?: string | null
  assignment?: Record<string, unknown> | null
  sla_hours?: number | null
  fields?: Array<Record<string, unknown>>
  triggers?: Array<Record<string, unknown>>
  gateway_mode?: string
  decision_table?: Record<string, unknown>
  service?: Record<string, unknown>
  notification?: Record<string, unknown>
  timer?: Record<string, unknown>
  outcome?: string | null
  action_status?: string | null
  position?: { x: number; y: number }
}

export interface WorkflowGraph {
  steps?: Record<string, WorkflowStepDefinition>
  transitions?: WorkflowTransition[]
  bindings?: WorkflowBinding[]
}

export interface StepNodeData {
  key: string
  type: WorkflowStepType
  name: string
  name_cn?: string
  role?: string | null
  assignment?: Record<string, unknown> | null
  sla_hours?: number | null
  fields?: Array<Record<string, unknown>>
  triggers?: Array<Record<string, unknown>>
  gateway_mode?: string
  decision_table?: Record<string, unknown>
  service?: Record<string, unknown>
  notification?: Record<string, unknown>
  timer?: Record<string, unknown>
  outcome?: string | null
  action_status?: string | null
}

export interface ValidationError {
  message: string
  severity: 'error' | 'warning'
}

export interface NodeTypeDefinition {
  type: WorkflowStepType
  color: string
  icon: string
  label: string
  description: string
}

export const NODE_TYPE_DEFINITIONS: NodeTypeDefinition[] = [
  { type: 'Task', color: '#2563eb', icon: '📝', label: 'Task', description: 'A user completes work or enters data before the process continues.' },
  { type: 'Approval', color: '#059669', icon: '✅', label: 'Approval', description: 'A user accepts or rejects an item and can drive approval outcomes.' },
  { type: 'Gateway', color: '#f59e42', icon: '🔀', label: 'Gateway', description: 'A decision point that branches the workflow based on conditions or outcomes.' },
  { type: 'Service', color: '#a21caf', icon: '⚙️', label: 'Service', description: 'A system step that runs configured logic without manual user work.' },
  { type: 'Notification', color: '#eab308', icon: '🔔', label: 'Notification', description: 'A system step that sends alerts or messages to users.' },
  { type: 'Timer', color: '#f43f5e', icon: '⏰', label: 'Timer', description: 'A waiting step that pauses the workflow until a timeout or deadline.' },
  { type: 'Join', color: '#0ea5e9', icon: '🔗', label: 'Join', description: 'A merge point that waits for multiple incoming branches before continuing.' },
  { type: 'End', color: '#64748b', icon: '🏁', label: 'End', description: 'The terminal step that closes the workflow path.' },
]

const NODE_TYPE_MAP = new Map(NODE_TYPE_DEFINITIONS.map((item) => [item.type, item]))

export function getNodeTypeDefinition(type: string | undefined | null): NodeTypeDefinition {
  return NODE_TYPE_MAP.get(type as WorkflowStepType) || { type: 'Task', color: '#64748b', icon: '❓', label: 'Task', description: 'Generic workflow step.' }
}

export function getPortCounts(type: string | undefined | null) {
  if (type === 'End') {
    return { inputs: 1, outputs: 0 }
  }
  if (type === 'Join') {
    return { inputs: 2, outputs: 1 }
  }
  if (type === 'Gateway') {
    return { inputs: 1, outputs: 2 }
  }
  return { inputs: 1, outputs: 1 }
}

function getHandles(type: WorkflowStepType) {
  const ports = getPortCounts(type)
  const targetHandles = ports.inputs === 2
    ? [
        { id: 'input-1', top: '33%' },
        { id: 'input-2', top: '67%' },
      ]
    : ports.inputs > 0
      ? [{ id: 'input-1', top: '50%' }]
      : []
  const sourceHandles = ports.outputs === 2
    ? [
        { id: 'output-1', top: '33%' },
        { id: 'output-2', top: '67%' },
      ]
    : ports.outputs > 0
      ? [{ id: 'output-1', top: '50%' }]
      : []

  return { targetHandles, sourceHandles }
}

function StepNodeBase({ data, selected }: NodeProps<StepNodeData>) {
  const nodeType = getNodeTypeDefinition(data.type)
  const { targetHandles, sourceHandles } = getHandles(data.type)

  return (
    <div
      style={{
        position: 'relative',
        minWidth: 152,
        maxWidth: 190,
        borderRadius: 14,
        border: selected ? '1.5px solid #0d6efd' : '1px solid rgba(148, 163, 184, 0.34)',
        background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        boxShadow: selected ? '0 10px 24px rgba(13, 110, 253, 0.14)' : '0 6px 18px rgba(15, 23, 42, 0.06)',
        padding: '10px 12px',
        color: '#0f172a',
        textAlign: 'left',
      }}
    >
      {targetHandles.map((handle, index) => (
        <Handle
          key={handle.id}
          id={handle.id}
          type="target"
          position={Position.Left}
          style={{ top: handle.top, left: -7, width: 12, height: 12, borderColor: nodeType.color, background: '#fff' }}
          isConnectable={data.type !== 'End'}
        />
      ))}
      {sourceHandles.map((handle) => (
        <Handle
          key={handle.id}
          id={handle.id}
          type="source"
          position={Position.Right}
          style={{ top: handle.top, right: -7, width: 12, height: 12, borderColor: nodeType.color, background: '#fff' }}
          isConnectable={data.type !== 'End'}
        />
      ))}

      <div className="d-flex align-items-start gap-2">
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            background: nodeType.color,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            fontSize: 16,
          }}
          title={nodeType.label}
        >
          {nodeType.icon}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1.2, color: '#0f172a' }}>
            {data.name}
          </div>
          {data.name_cn && data.name_cn !== data.name && (
            <div style={{ fontSize: 10, color: '#64748b', marginTop: 2, lineHeight: 1.2 }}>
              {data.name_cn}
            </div>
          )}
          <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px 7px',
                borderRadius: 999,
                background: `${nodeType.color}14`,
                color: nodeType.color,
                fontSize: 10,
                fontWeight: 600,
              }}
              title={nodeType.description}
            >
              {nodeType.label}
            </span>
            {data.sla_hours ? (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px 7px',
                  borderRadius: 999,
                  background: '#f8fafc',
                  color: '#334155',
                  fontSize: 10,
                  fontWeight: 600,
                }}
              >
                SLA {data.sla_hours}h
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

function createNodeComponent(type: WorkflowStepType) {
  return memo(function WorkflowNode(props: NodeProps<StepNodeData>) {
    return <StepNodeBase {...props} data={{ ...props.data, type }} />
  })
}

export const TaskNode = createNodeComponent('Task')
export const ApprovalNode = createNodeComponent('Approval')
export const GatewayNode = createNodeComponent('Gateway')
export const ServiceNode = createNodeComponent('Service')
export const NotificationNode = createNodeComponent('Notification')
export const TimerNode = createNodeComponent('Timer')
export const JoinNode = createNodeComponent('Join')
export const EndNode = createNodeComponent('End')

export const workflowNodeTypes = {
  Task: TaskNode,
  Approval: ApprovalNode,
  Gateway: GatewayNode,
  Service: ServiceNode,
  Notification: NotificationNode,
  Timer: TimerNode,
  Join: JoinNode,
  End: EndNode,
}

export function createStepKey(base: string, existingKeys: Set<string>) {
  const normalized = (base || 'step')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'step'

  let candidate = normalized
  let suffix = 2
  while (existingKeys.has(candidate)) {
    candidate = `${normalized}_${suffix}`
    suffix += 1
  }
  return candidate
}

function buildOrderMap(stepKeys: string[], transitions: Array<{ from: string; to: string }>, positions: Record<string, { x: number; y: number }>) {
  const incomingCount = new Map<string, number>()
  stepKeys.forEach((key) => incomingCount.set(key, 0))
  transitions.forEach((transition) => {
    incomingCount.set(transition.to, (incomingCount.get(transition.to) || 0) + 1)
  })

  let roots = stepKeys.filter((key) => (incomingCount.get(key) || 0) === 0)
  if (roots.length === 0 && stepKeys.length > 0) {
    roots = [...stepKeys].sort((left, right) => (positions[left]?.x || 0) - (positions[right]?.x || 0)).slice(0, 1)
  }

  const orderMap = new Map<string, number>()
  roots.forEach((key) => orderMap.set(key, 1))

  for (let pass = 0; pass < stepKeys.length; pass += 1) {
    let changed = false
    transitions.forEach((transition) => {
      const fromOrder = orderMap.get(transition.from)
      if (!fromOrder) {
        return
      }
      const nextOrder = fromOrder + 1
      if (!orderMap.has(transition.to) || nextOrder > (orderMap.get(transition.to) || 0)) {
        orderMap.set(transition.to, nextOrder)
        changed = true
      }
    })
    if (!changed) {
      break
    }
  }

  stepKeys.forEach((key) => {
    if (!orderMap.has(key)) {
      orderMap.set(key, 1)
    }
  })

  return orderMap
}

export function toWorkflowGraph(nodes: Array<Node<StepNodeData>>, edges: Edge[], bindings: WorkflowBinding[]) {
  const positions = Object.fromEntries(nodes.map((node) => [node.data.key, node.position || { x: 0, y: 0 }]))
  const transitions = edges.map((edge) => {
    const sourceNode = nodes.find((node) => node.id === edge.source)
    const targetNode = nodes.find((node) => node.id === edge.target)
    return {
      from: sourceNode?.data.key || '',
      to: targetNode?.data.key || '',
      label_en: typeof edge.label === 'string' && edge.label ? edge.label : (edge.data as any)?.label_en || 'Next',
      label_cn: (edge.data as any)?.label_cn || '下一步',
      type: (edge.data as any)?.type || 'normal',
    }
  }).filter((transition) => transition.from && transition.to)

  const orderMap = buildOrderMap(nodes.map((node) => node.data.key), transitions, positions)

  const steps = Object.fromEntries(nodes.map((node) => {
    const { key, type, name, name_cn, role, assignment, sla_hours, fields, triggers, gateway_mode, decision_table, service, notification, timer, outcome, action_status } = node.data
    return [
      key,
      {
        name_en: name || node.id,
        name_cn: name_cn || name || node.id,
        type,
        order: orderMap.get(key) || 1,
        role: role || null,
        assignment,
        sla_hours: sla_hours ?? null,
        fields: fields || [],
        triggers: triggers || [],
        gateway_mode,
        decision_table,
        service,
        notification,
        timer,
        outcome: outcome ?? null,
        action_status: action_status ?? null,
        position: node.position || { x: 0, y: 0 },
      },
    ]
  }))

  return {
    steps,
    transitions,
    bindings,
  }
}

export function toReactFlowGraph(graph: WorkflowGraph) {
  const stepEntries = Object.entries(graph?.steps || {}) as Array<[string, WorkflowStepDefinition]>
  const groupedByOrder = new Map<number, Array<[string, WorkflowStepDefinition]>>()

  stepEntries.forEach(([stepKey, stepDef]) => {
    const order = Number(stepDef.order) || 1
    if (!groupedByOrder.has(order)) {
      groupedByOrder.set(order, [])
    }
    groupedByOrder.get(order)?.push([stepKey, stepDef])
  })

  const orderedGroups = [...groupedByOrder.entries()].sort((left, right) => left[0] - right[0])
  const nodes: Array<Node<StepNodeData>> = []
  const stepIdMap = new Map<string, string>()

  orderedGroups.forEach(([order, stepsAtOrder]) => {
    stepsAtOrder.forEach(([stepKey, stepDef], index) => {
      const nodeId = stepKey
      stepIdMap.set(stepKey, nodeId)
      const fallbackPosition = { x: (order - 1) * 240 + 40, y: index * 140 + 40 }
      nodes.push({
        id: nodeId,
        type: stepDef.type || 'Task',
        position: stepDef.position || fallbackPosition,
        data: {
          key: stepKey,
          type: stepDef.type || 'Task',
          name: stepDef.name_en || stepKey,
          name_cn: stepDef.name_cn || stepDef.name_en || stepKey,
          role: stepDef.role || null,
          assignment: stepDef.assignment,
          sla_hours: stepDef.sla_hours ?? null,
          fields: stepDef.fields || [],
          triggers: stepDef.triggers || [],
          gateway_mode: stepDef.gateway_mode,
          decision_table: stepDef.decision_table,
          service: stepDef.service,
          notification: stepDef.notification,
          timer: stepDef.timer,
          outcome: stepDef.outcome ?? null,
          action_status: stepDef.action_status ?? null,
        },
      })
    })
  })

  const edges: Edge[] = (graph?.transitions || []).map((transition, index) => ({
    id: `edge-${index + 1}`,
    source: stepIdMap.get(transition.from) || '',
    target: stepIdMap.get(transition.to) || '',
    type: 'smoothstep',
    label: transition.label_en || 'Next',
    markerEnd: { type: MarkerType.ArrowClosed },
    data: {
      label_en: transition.label_en || 'Next',
      label_cn: transition.label_cn || '下一步',
      type: transition.type || 'normal',
    },
  })).filter((edge) => edge.source && edge.target)

  return {
    nodes,
    edges,
    bindings: Array.isArray(graph?.bindings) ? graph.bindings : [],
  }
}

function countConnections(edges: Edge[], nodeId: string, kind: 'incoming' | 'outgoing') {
  return edges.filter((edge) => (kind === 'incoming' ? edge.target === nodeId : edge.source === nodeId)).length
}

export function canConnectWorkflowNodes(nodes: Array<Node<StepNodeData>>, edges: Edge[], connection: Connection) {
  const sourceId = connection.source ? String(connection.source) : ''
  const targetId = connection.target ? String(connection.target) : ''

  if (!sourceId || !targetId || sourceId === targetId) {
    return false
  }

  const sourceNode = nodes.find((node) => String(node.id) === sourceId)
  const targetNode = nodes.find((node) => String(node.id) === targetId)

  if (!sourceNode || !targetNode) {
    return false
  }

  if (sourceNode.data.type === 'End') {
    return false
  }

  const sourceConnections = countConnections(edges, sourceId, 'outgoing')
  const targetConnections = countConnections(edges, targetId, 'incoming')

  if (sourceNode.data.type === 'Gateway') {
    if (sourceConnections >= 2) {
      return false
    }
  } else if (sourceConnections >= 1) {
    return false
  }

  if (targetNode.data.type === 'Join') {
    return true
  }

  return targetConnections < 1
}

export function validateFlowGraph(nodes: Array<Node<StepNodeData>>, edges: Edge[]): ValidationError[] {
  const errors: ValidationError[] = []

  if (nodes.length < 2) {
    errors.push({ message: 'Graph must have at least 2 nodes', severity: 'error' })
  }

  if (edges.length < 1 && nodes.length > 1) {
    errors.push({ message: 'Graph must have at least 1 connection', severity: 'error' })
  }

  const nodeIds = new Set(nodes.map((node) => String(node.id)))
  for (const edge of edges) {
    if (!nodeIds.has(String(edge.source))) {
      errors.push({ message: `Connection references missing source node ${String(edge.source)}`, severity: 'error' })
    }
    if (!nodeIds.has(String(edge.target))) {
      errors.push({ message: `Connection references missing target node ${String(edge.target)}`, severity: 'error' })
    }
  }

  const endNodes = nodes.filter((node) => node.data.type === 'End')
  if (endNodes.length === 0 && nodes.length > 0) {
    errors.push({ message: 'Graph must have at least one End node', severity: 'error' })
  }

  for (const endNode of endNodes) {
    if (edges.some((edge) => edge.source === endNode.id)) {
      errors.push({ message: `End node "${endNode.data.name}" has outgoing connections`, severity: 'error' })
    }
    if (!edges.some((edge) => edge.target === endNode.id)) {
      errors.push({ message: `End node "${endNode.data.name}" has no incoming connections`, severity: 'warning' })
    }
  }

  for (const node of nodes) {
    if (node.data.type === 'Join') {
      const incoming = edges.filter((edge) => edge.target === node.id)
      if (incoming.length < 2) {
        errors.push({ message: `Join "${node.data.name}" needs ≥2 incoming (has ${incoming.length})`, severity: 'error' })
      }
    }
  }

  if (nodes.length > 1) {
    const roots = nodes.filter((node) => !edges.some((edge) => edge.target === node.id) && node.data.type !== 'End')
    if (roots.length === 0) {
      errors.push({ message: 'No start node found (node with no incoming connections)', severity: 'error' })
    }

    const reachable = new Set<string>()
    const queue = roots.map((node) => String(node.id))
    while (queue.length > 0) {
      const current = queue.shift()!
      if (reachable.has(current)) {
        continue
      }
      reachable.add(current)
      for (const edge of edges) {
        if (edge.source === current && !reachable.has(String(edge.target))) {
          queue.push(String(edge.target))
        }
      }
    }

    const orphans = nodes.filter((node) => !reachable.has(String(node.id)))
    if (orphans.length > 0) {
      errors.push({ message: `Orphan nodes: ${orphans.map((node) => node.data.name).join(', ')}`, severity: 'warning' })
    }
  }

  return errors
}
