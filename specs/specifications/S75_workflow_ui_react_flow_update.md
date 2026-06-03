# S75 — Workflow UI Update with React Flow

> **Date**: 2026-03-19  
> **Status**: ✅ Current  
> **Level**: L3 + L4  
> **Depends on**: R16, S16, S25, S70, S80  
> **Related batch**: WF-24  
> **Purpose**: Document the React-native workflow builder canvas built on `@xyflow/react` while preserving the existing workflow graph API contract.

---

## 1. Overview

This specification defines the as-built React Flow workflow template builder in ActionHub.

Operating-model note for this spec:

- the builder designs **process workflow templates** for standalone business processes such as ECO, account / ID creation, approvals, and similar request-driven procedures
- the primary launch context for these workflows is the existing workflow area, not an existing action detail page
- this spec does not require or imply a new dedicated process-start page or separate process-start product surface
- actions and workflow steps may be shown on the same user dashboard, but in separate panels and as separate record types

The implemented update has one core goal:

- provide a fully React-based React Flow canvas for workflow authoring.

This is a **frontend architecture and interaction** change, not a workflow-engine redesign.

The following must remain stable:

- workflow template persistence in `t_workflow_template.wft_graph`
- backend graph validation rules defined in S70
- step types, transition semantics, and runtime engine behavior in S70 and S72
- builder route `/workflow/builder`
- save/load API endpoints already used by the builder

This spec records the gap that has now been closed:

- S70 and S80 already describe the React Flow target
- the builder now lives in `action_hub/frontend/src/pages/workflow/WorkflowBuilder.tsx` with React Flow-based state and rendering

S75 is the authoritative detailed UI spec for the completed migration and subsequent builder refinements.

---

## 2. Objectives

### 2.1 Product Goals

- Make the builder a first-class React screen with predictable state updates.
- Remove fragile custom DOM manipulation for nodes, links, and drag behavior.
- Improve builder usability for templates with parallel branches, joins, and multiple end states.
- Keep authoring bilingual and API-first.
- Reduce maintenance cost by aligning implementation with the existing React SPA architecture.

### 2.2 Technical Goals

- Replace Drawflow instance state with React Flow `nodes` and `edges` state.
- Preserve serialization to the existing `steps` and `transitions` JSON schema.
- Normalize node IDs consistently as strings in UI state.
- Support typed custom node components for all 8 workflow step types.
- Centralize builder validation and surface it live in the UI.

### 2.3 Non-Goals

- No workflow engine behavior changes.
- No new backend graph format.
- No BPMN import/export.
- No collaborative multi-user editing.
- No runtime workflow workbench redesign; that remains covered by S73.
- No unrestricted visual styling system outside the existing Bootstrap-based frontend approach.
- No assumption that newly created actions are the default parent object for workflows.

---

## 3. Historical Gap (Closed by WF-24)

### 3.1 Pre-WF-24 Builder Constraints

Before WF-24, the builder had the following limitations:

- node and edge rendering are manually managed in the DOM
- connection lines are custom SVG elements rendered outside a React graph abstraction
- selection, drag, and linking behavior rely on imperative refs
- tests depend on Drawflow mocks rather than React component contracts
- package metadata and architecture docs indicated React Flow, but the implementation had not yet caught up

### 3.2 Resulting Risks (Pre-Migration)

- inconsistent state between React and the canvas DOM
- fragile connection rendering and deletion behavior
- high cost for adding richer tooling such as minimap, fit-view, or typed handles
- reduced confidence in save/load correctness during canvas mutations

---

## 4. Design Principles

### 4.1 Renderer Change Only

The migration is a **renderer replacement**, not a graph model rewrite.

- React Flow manages the visual graph.
- ActionHub remains responsible for graph semantics.
- The persisted graph stays in ActionHub's existing JSON format.

### 4.2 Inspector-Driven Editing

Node creation and connection happen on the canvas. Detailed step editing happens in an inspector surface, not inside inline editable node cards.

### 4.3 Immediate Validation

The builder must show validation feedback as authors edit the graph, rather than only on save.

### 4.4 Stable Mental Model

Workflow authors must continue to think in ActionHub terms:

- step
- transition
- assignment
- SLA
- field set
- bindings

They should not need to think in terms of "create an action first, then maybe attach a workflow" as the default authoring or runtime model. The default mental model is a standalone process workflow launched from workflow-specific UI.

React Flow is an implementation detail, not a user-facing concept.

### 4.5 Accessibility and Keyboard Safety

The UI must remain operable without precision mouse behavior for the critical non-canvas actions:

- template selection
- save
- validate
- step property editing
- deletion confirmation

---

## 5. Screen Model

### 5.1 Route

- Path: `/workflow/builder`
- Auth: required
- Authorization: Admin and TeamLead per existing builder permissions in R16 and S72

### 5.2 Page Regions

The builder page is composed of 5 regions:

1. **Template header bar**
2. **Palette rail**
3. **Canvas workspace**
4. **Inspector panel**
5. **Validation and status strip**

### 5.3 Layout

Desktop layout uses a three-column structure:

- left: palette rail, compact and scrollable
- center: canvas workspace, dominant visual area
- right: inspector panel for selected node/edge/template settings

Tablet-width layout collapses to:

- header
- canvas
- tabbed bottom drawer for palette and inspector

Mobile editing is not a primary target, but the page must remain viewable and non-broken.

---

## 6. Template Header Bar

### 6.1 Content

The header bar must show:

- builder title
- template selector or template identity summary
- workflow type badge: `action` or `request`
- dirty-state indicator
- primary save button
- secondary validate button
- canvas utility actions: `Fit View`, `Center`, `Zoom In`, `Zoom Out`

### 6.2 Save State Model

Three save states are required:

- `Saved`
- `Unsaved changes`
- `Saving...`

If save fails, the header bar must surface:

- error badge
- concise message
- retry affordance

### 6.3 Dirty-State Rule

Dirty state becomes true when any of the following changes:

- node created, moved, deleted, or edited
- edge created or deleted
- bindings changed
- template metadata changed

Dirty state resets only after a successful save or explicit template reload.

---

## 7. Palette Rail

### 7.1 Purpose

The palette is the source for creating workflow steps.

### 7.2 Node Types

The palette must expose all 8 step types defined in S70:

- Task
- Approval
- Gateway
- Service
- Notification
- Timer
- Join
- End

### 7.3 Palette Item Content

Each palette item shows:

- icon
- bilingual label support through `useTranslation()`
- step-type color
- tooltip with concise semantic description

### 7.4 Creation Interaction

The default creation gesture is drag-and-drop from palette to canvas.

The UI must also support a non-drag alternative:

- click a palette item while a canvas insertion mode is active, then click canvas to place

This fallback is required for accessibility and lower-precision input devices.

### 7.5 Default Step Initialization

When a node is created, the builder must initialize:

- `id` as a string UUID or unique string token
- `data.key` using ActionHub step-key normalization rules
- `data.type`
- default bilingual names based on the step type
- default handle layout based on step type
- empty assignment and field config where applicable

Step key generation must remain collision-safe.

---

## 8. Canvas Workspace

### 8.1 Core Canvas Components

The React Flow canvas must include:

- `ReactFlow`
- `Background`
- `Controls`
- `MiniMap`

### 8.2 Canvas Behaviors

The canvas must support:

- pan
- zoom
- box selection
- node drag
- node selection
- edge selection
- deletion of selected nodes and edges
- fit-view

### 8.3 Visual Baseline

The canvas should visually communicate structure clearly rather than mimic BPMN notation.

Required visual rules:

- light neutral background with subtle grid or dots
- clear contrast between node body and canvas
- directed edges with arrow markers
- selected node and selected edge states visibly distinct
- validation errors visually tied to nodes or edges when possible

### 8.4 Empty State

When no nodes exist, the canvas must show an instructional empty state:

- brief explanation
- CTA to drag the first node from the palette
- optional quick actions: `Add Task`, `Add Approval`, `Add End`

---

## 9. Custom Node Specification

### 9.1 Node Component Model

Each step type must be rendered using a typed React Flow custom node component registered through `nodeTypes`.

Shared base node responsibilities:

- render icon
- render name
- render type badge
- render status markers such as validation warnings
- render source and target handles
- reflect selected state

### 9.2 Node Data Contract

Each node must carry a `StepNodeData` payload with at least:

```ts
type StepNodeData = {
  key: string
  type: 'Task' | 'Approval' | 'Gateway' | 'Service' | 'Notification' | 'Timer' | 'Join' | 'End'
  name: string
  name_cn?: string
  role?: string | null
  assignment?: Record<string, unknown>
  sla_hours?: number | null
  fields?: Array<Record<string, unknown>>
  triggers?: Array<Record<string, unknown>>
  gateway_mode?: 'exclusive' | 'inclusive'
  decision_table?: Record<string, unknown>
  service?: Record<string, unknown>
  notification?: Record<string, unknown>
  timer?: Record<string, unknown>
  outcome?: string | null
  action_status?: string | null
}
```

### 9.3 Per-Type Handle Rules

| Step Type | Target Handles | Source Handles | Rule |
|-----------|----------------|----------------|------|
| Task | 1 | 1 | standard human step |
| Approval | 1 | 1..2 | may later expose explicit reject path styling |
| Gateway | 1 | 2+ | supports branching |
| Service | 1 | 1 | engine-driven |
| Notification | 1 | 1 | engine-driven |
| Timer | 1 | 1..2 | supports normal and timeout semantics |
| Join | 2+ | 1 | must visually emphasize convergence |
| End | 1 | 0 | terminal step |

### 9.4 Node Visual Content

Human-facing node cards must show:

- primary title in English or current UI language
- step type badge
- optional SLA badge
- assignment summary for human steps

The card should not try to display full field definitions inline.

### 9.5 Selected State

Selected state must be emphasized with:

- distinct border ring
- subtle shadow lift
- inspector synchronization on click

---

## 10. Edge Specification

### 10.1 Edge Semantics

Edges remain the UI representation of workflow transitions.

They map to existing persisted transition objects:

```ts
type WorkflowTransition = {
  from: string
  to: string
  label_en?: string
  label_cn?: string
  type?: 'normal' | 'rejection' | 'timeout' | 'condition'
}
```

### 10.2 Edge Rendering

Required behaviors:

- directed arrows
- selectable edges
- deletable edges
- optional text labels when transition type is not default

### 10.3 Edge Editing

Selecting an edge opens edge properties in the inspector.

Editable fields:

- transition type
- English label
- Chinese label

For the first React Flow rollout, edge editing may remain minimal, but transition type must be supported where already defined by S70.

### 10.4 Connection Rules

The UI must prevent or block invalid connections where possible before save:

- self-loop unless explicitly allowed by a future spec
- outgoing edge from End
- insufficient incoming paths on Join not blocked immediately, but shown as validation error
- duplicate source-target connection when semantics are identical

---

## 11. Inspector Panel

### 11.1 Purpose

The inspector is the main editing surface for selected objects.

It replaces modal-heavy editing as the primary workflow.

### 11.2 Inspector Modes

The panel supports 4 modes:

- `Template`
- `Step`
- `Transition`
- `Nothing selected`

### 11.3 Template Mode

Editable template-level properties include:

- template name EN
- template name ZH
- workflow type
- default flag
- bindings

Bindings UI must continue to support current ActionHub scopes without backend contract changes.

### 11.4 Step Mode

The step inspector must show sections based on the selected node type.

Common sections:

- identity
- assignment
- SLA
- fields
- step-specific configuration

#### Common identity fields

- step key
- name EN
- name ZH
- type

#### Human-step sections

For `Task` and `Approval`:

- assignment mode
- default assignee configuration
- SLA hours
- form fields

#### Gateway sections

- gateway mode
- decision table editor summary
- route rule count

#### Service sections

- handler name
- input mapping summary
- output mapping summary
- on-error policy

#### Notification sections

- target role or user mode
- title template
- body template

#### Timer sections

- duration or SLA threshold
- escalation behavior
- timeout transition mapping

#### Join sections

- join mode if present in graph definition

#### End sections

- outcome label
- mapped action status

### 11.5 Transition Mode

When an edge is selected, the inspector must show:

- source step
- target step
- transition type
- label EN
- label ZH

### 11.6 NodeEditor Refactor Rule

The existing `NodeEditor` logic may be preserved, but the preferred UI form factor is:

- reusable editor component rendered inside the inspector panel

If a modal remains temporarily during migration, it must be treated as an interim implementation detail, not the target UX.

---

## 12. Validation UX

### 12.1 Validation Sources

The builder has two validation layers:

1. **client-side structural validation**
2. **server-side authoritative validation** via existing API save/validate behavior

### 12.2 Client-Side Rules

The builder must validate at least:

- graph has at least 2 nodes when non-empty template is being authored
- graph has at least 1 connection when multiple nodes exist
- at least 1 End node exists
- End nodes have no outgoing edges
- Join nodes have enough incoming edges
- there is at least 1 reachable root
- orphan nodes are detected
- duplicate step keys are blocked

### 12.3 Validation Surfaces

Validation feedback must appear in three places:

- summary strip above or below the canvas
- inline node or edge highlights where targetable
- blocking error list on save failure

### 12.4 Severity Levels

Two severity levels are required:

- `error`: cannot save
- `warning`: may save, but author should review

### 12.5 Save Blocking Rules

Save must be blocked for structural errors.

Warnings do not block save unless backend validation rejects the graph.

---

## 13. Serialization and Data Compatibility

### 13.1 Compatibility Contract

React Flow UI state must serialize to the existing backend graph shape.

No backend schema change is introduced by this spec.

### 13.2 Required Conversion Functions

The frontend must provide two canonical transforms:

```ts
function toWorkflowGraph(nodes: Node<StepNodeData>[], edges: Edge[], bindings: WorkflowBinding[]): WorkflowGraph

function toReactFlowGraph(graph: WorkflowGraph): {
  nodes: Node<StepNodeData>[]
  edges: Edge[]
  bindings: WorkflowBinding[]
}
```

### 13.3 ID Normalization

UI node IDs must always be treated as strings.

Required rule:

- all selection, lookup, and edge construction logic normalizes IDs with `String(...)`

This avoids silent lookup failures caused by mixed numeric and string node IDs during save/edit cycles.

### 13.4 Position Persistence

Node positions remain stored in the graph under the step definition, using the existing `position` object.

If a legacy graph lacks positions, the UI must generate deterministic fallback positions during import.

---

## 14. Component Architecture

### 14.1 Target Frontend Structure

The React Flow builder should be decomposed into focused components:

```text
src/pages/workflow/
  Builder.tsx
src/components/workflow/
  BuilderHeader.tsx
  BuilderValidationStrip.tsx
  NodePalette.tsx
  BuilderInspector.tsx
  EdgeEditor.tsx
  nodes/
    StepNode.tsx
    TaskNode.tsx
    ApprovalNode.tsx
    GatewayNode.tsx
    ServiceNode.tsx
    NotificationNode.tsx
    TimerNode.tsx
    JoinNode.tsx
    EndNode.tsx
```

### 14.2 State Ownership

`Builder.tsx` remains the orchestration component and owns:

- selected template
- selected node id
- selected edge id
- nodes state
- edges state
- bindings state
- dirty state
- validation state

### 14.3 Hook Usage

Preferred React Flow integration:

- `useNodesState`
- `useEdgesState`
- `ReactFlowProvider`

The builder may also use `useReactFlow()` for `fitView()` and projection helpers.

### 14.4 Data Fetching

Template loading and saving must continue to use the existing API client and current route-level data patterns.

This spec does not require TanStack Query for the entire canvas editing state.

---

## 15. Interaction Flows

### 15.1 Create Step Flow

1. User drags `Task` from palette to canvas.
2. Builder computes drop position in canvas coordinates.
3. Node is added with default data.
4. Node becomes selected.
5. Inspector opens in `Step` mode.
6. User edits name, assignment, and fields.

### 15.2 Connect Steps Flow

1. User drags from source handle to target handle.
2. Builder checks whether the connection is structurally valid.
3. Edge is added.
4. If non-default transition behavior is needed, inspector opens in `Transition` mode.

### 15.3 Edit Step Flow

1. User clicks an existing node.
2. Inspector shows current values.
3. Changes update node data in React state.
4. Dirty state becomes true.
5. Validation reruns.

### 15.4 Delete Flow

Node deletion behavior:

- selected node delete must prompt confirmation if it has one or more connections
- deleting a node also removes attached edges

Edge deletion behavior:

- may be immediate without confirmation

### 15.5 Save Flow

1. User clicks `Save`.
2. Builder runs client validation.
3. If blocking errors exist, save is not attempted.
4. If valid, builder serializes graph to API payload.
5. Backend validates graph.
6. On success, dirty state resets.
7. On failure, backend error messages are surfaced in the validation strip.

---

## 16. Internationalization

### 16.1 General Rule

All visible builder text must use `useTranslation()` or the repo's current i18n utility. No hardcoded user-facing strings are allowed in new UI components.

### 16.2 Required String Domains

The builder update must provide translation coverage for:

- canvas actions
- node tooltips
- validation messages
- inspector section titles
- empty states
- save-state messages

### 16.3 Language Behavior

The canvas node body may prioritize one visible display label at a time for readability, but the inspector must allow editing both:

- English name
- Chinese name

---

## 17. Accessibility

### 17.1 Required Accessibility Baseline

The updated builder must support:

- visible keyboard focus states
- descriptive labels for form controls
- non-color-only indication of validation errors
- tooltips or text alternatives for icon-only actions

### 17.2 Keyboard Support

Required keyboard actions:

- `Delete` or `Backspace` for selected edge or node deletion where safe
- `Escape` to clear selection
- `Ctrl+S` to save
- tab navigation through inspector fields and header controls

Canvas drag precision itself does not need full keyboard parity in the first delivery, but destructive and save actions must remain keyboard-safe.

---

## 18. Performance Requirements

### 18.1 Target Scale

The builder must remain responsive for typical templates up to:

- 50 nodes
- 80 edges

### 18.2 Expected Behaviors

- node drag should feel immediate
- validation should not visibly block typing in the inspector
- template load should complete without manual DOM redraw loops

### 18.3 Optimization Guidance

- avoid storing redundant derived graph structures in multiple places
- memoize node type registry and static metadata
- separate visual selection state from persisted graph payload when practical

---

## 19. Error Handling

### 19.1 Template Load Failure

If a template cannot be loaded:

- show an inline error card
- preserve the rest of the page shell
- provide retry

### 19.2 Graph Import Failure

If persisted graph JSON cannot be converted to React Flow state:

- show a blocking error with template id and version context
- do not render a partially broken canvas silently

### 19.3 Save Failure

Save failures must distinguish:

- network failure
- validation failure
- authorization failure
- unknown server error

---

## 20. Testing Specification

### 20.1 Frontend Test Scope

The builder update must include tests for:

- rendering the builder page without Drawflow globals
- palette item rendering
- node creation handler logic
- graph serialization round-trip
- validation behavior for missing End node and orphan nodes
- save blocking when client-side structural errors exist

### 20.2 Test Strategy

Frontend tests may mock React Flow primitives, but must not rely on Drawflow window mocks.

### 20.3 Manual Smoke Test Matrix

Minimum manual verification:

1. Load an existing template and confirm nodes/edges appear correctly.
2. Create one step of each of the 8 types.
3. Connect nodes and save.
4. Reload the template and confirm no data loss.
5. Delete a connected node and confirm edge cleanup.
6. Create an invalid graph and confirm save is blocked.

---

## 21. Migration Plan

### 21.1 Phase 1 — Dependency and Canvas Shell

- add `@xyflow/react`
- add React Flow CSS
- create node registry and canvas shell
- keep existing API load/save logic

### 21.2 Phase 2 — State Migration

- replace Drawflow refs with React Flow state hooks
- replace custom connection rendering and imperative drag logic
- preserve serialization functions

### 21.3 Phase 3 — Inspector and Validation

- move node editing into inspector-driven workflow
- integrate live validation strip
- add edge editing support

### 21.4 Phase 4 — Cleanup

- remove Drawflow script references and mocks
- delete obsolete imperative canvas code
- align tests and architecture docs

---

## 22. Acceptance Criteria

The React Flow UI update is complete when all of the following are true:

- the builder no longer depends on Drawflow runtime objects
- the builder route renders a React Flow canvas with nodes and edges from persisted templates
- all 8 step types render as typed custom nodes
- users can create, select, connect, edit, and delete nodes and edges
- template save/load round-trips without graph contract changes
- client-side validation surfaces structural errors before save
- the UI includes minimap, controls, and fit-view behavior
- builder text is localized through the existing i18n approach
- tests no longer mock `window.Drawflow`
- the implementation aligns the codebase with the React Flow claims already documented in S70 and S80

---

## 23. Implementation Notes

### 23.1 Preserved Backend Contract

Backend services and database schema do not need changes for this spec unless later implementation uncovers a missing transition property or validation endpoint mismatch.

### 23.2 Recommended File Targets

Primary implementation files are expected to include:

- `action_hub/frontend/src/pages/workflow/Builder.tsx`
- `action_hub/frontend/src/components/workflow/NodePalette.tsx`
- `action_hub/frontend/src/components/workflow/NodeEditor.tsx`
- new node components under `action_hub/frontend/src/components/workflow/nodes/`

### 23.3 Relationship to Other Specs

- S70 remains the source of truth for workflow graph semantics.
- S72 remains the source of truth for assignment-rule semantics.
- S73 remains the source of truth for runtime workflow execution UI.
- S80 remains the as-built React frontend reference and should be updated after implementation to reflect final component structure.
