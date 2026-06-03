# ActionHub — Specifications Index

> **Last updated**: 2026-03-23  
> **Methodology**: Merise-inspired — Requirements (R) define *what*, Specifications (S) define *how*

---

## Reading Order

1. Start with [context.md](context.md) for project background and constraints
2. Read [requirements/I00_intent.md](requirements/I00_intent.md) for strategic intent
3. Read [requirements/R00_initial_vision.md](requirements/R00_initial_vision.md) for full project vision
4. Browse requirements by domain (R01–R20) as needed
5. Reference specifications (S00–S80) for technical implementation details

---

## Status Legend

| Badge | Meaning |
|-------|---------|
| ✅ Current | Actively maintained, reflects as-built state |
| ⚠️ Partially Stale | Some sections reference retired technologies (Jinja2/HTMX); valid content noted inline |
| 📋 Planned | Specified but not yet implemented |
| 🗄️ Archived | Fully superseded; kept for historical reference |

---

## Context

| File | Description | Status |
|------|------------|--------|
| [context.md](context.md) | Organization profile, tech stack, constraints, design decisions, project timeline | ✅ Current |

---

## Requirements (R-series) — *What* the system must do

> **Merise layer**: Expression des Besoins

| File | Domain | Merise Level | Status | Key Dependencies |
|------|--------|-------------|--------|-----------------|
| [I00_intent.md](requirements/I00_intent.md) | Strategic intent | L0 — Intent | ✅ Current | None (root) |
| [R00_initial_vision.md](requirements/R00_initial_vision.md) | Project vision, goals, delivery scope | L1 — Requirements | ✅ Current | I00 |
| [R01_entities.md](requirements/R01_entities.md) | Entity model (actions, users, teams, etc.) | L1 | ✅ Current | R00 |
| [R02_action_lifecycle.md](requirements/R02_action_lifecycle.md) | Status FSM, priorities, SLA | L1 | ✅ Current | R01 |
| [R03_assignment_workflow.md](requirements/R03_assignment_workflow.md) | Lead-based action accountability model | L1 | ✅ Current | R01 |
| [R04_notifications.md](requirements/R04_notifications.md) | In-app bell, email, reminders | L1 | ✅ Current | R01, R03 |
| [R05_dashboards_reporting.md](requirements/R05_dashboards_reporting.md) | KPIs, charts, Excel export, report builder | L1 | ✅ Current | R01, R02 |
| [R06_security.md](requirements/R06_security.md) | Auth, RBAC, audit, session/token | L1 | ✅ Current | R00 |
| [R07_data_import.md](requirements/R07_data_import.md) | Excel import, mapping, dedup | L1 | ✅ Current | R01 |
| [R08_taxonomy.md](requirements/R08_taxonomy.md) | Teams, categories, tags | L1 | ✅ Current | R00 |
| [R09_ui_content.md](requirements/R09_ui_content.md) | UI layout, i18n, accessibility | L1 | ✅ Current | R00 |
| [R11_agent_framework.md](requirements/R11_agent_framework.md) | AI agents, automation (V3+ vision) | L1 | 📋 Planned | R02, R03 |
| [R13_testing.md](requirements/R13_testing.md) | Test strategy, coverage targets | L1 | ✅ Current | All |
| [R14_pilot_deployment.md](requirements/R14_pilot_deployment.md) | Deployment plan, rollout | L1 | ✅ Current | R00 |
| [R15_participants_notifications.md](requirements/R15_participants_notifications.md) | Meeting participants, notifications | L1 | ✅ Current | R04 |
| [R16_workflow_app_extension.md](requirements/R16_workflow_app_extension.md) | Workflow V2 requirements | L1 | ✅ Current | R00 |
| [R17_meeting_decisions.md](requirements/R17_meeting_decisions.md) | Meeting decision tracking | L1 | ✅ Current | R01 |
| [R19_meeting_series_workspace.md](requirements/R19_meeting_series_workspace.md) | Meeting series workspace, default participants, occurrence comments, MoM PDF | L1 | 🚧 In Progress | R15, R17 |
| [R20_access_control_governance_addendum.md](requirements/R20_access_control_governance_addendum.md) | Access control governance addendum for personal/team dashboard and meeting-content permissions | L1 | ✅ Current | R05, R06, R19, S16 |
| [DECISIONS.md](requirements/DECISIONS.md) | Architectural decision log (D1–D214) | — | ✅ Current | All |

---

## Specifications (S-series) — *How* to implement

> **Merise layers**: L2 Conceptual → L3 Logical → L4 Physical

| File | Domain | Merise Level | Status | Depends On |
|------|--------|-------------|--------|-----------|
| [S00_initial_vision.md](specifications/S00_initial_vision.md) | Vision spec (mirrors R00) | L2 — Conceptual | ✅ Current | R00, context.md |
| [S02_functional_scope.md](specifications/S02_functional_scope.md) | Functional scope matrix | L2 | ✅ Current | R00 |
| [S05_data_dictionary.md](specifications/S05_data_dictionary.md) | All entities, fields, types, constraints | L2 | ✅ Current | R01 |
| [S10_MCD.md](specifications/S10_MCD.md) | Conceptual data model (Entity-Relationship) | L2 | ✅ Current | S05 |
| [S11_MCT.md](specifications/S11_MCT.md) | Conceptual treatment model (process flows) | L2 | ✅ Current | S10 |
| [S15_MOT.md](specifications/S15_MOT.md) | Operational treatment model (actors, operations) | L3 — Logical | ✅ Current | S11 |
| [S16_API_Contract.md](specifications/S16_API_Contract.md) | REST API contract (all endpoints) | L3 | ✅ Current | S15 |
| [S20_MLD.md](specifications/S20_MLD.md) | Logical data model (DDL, indexes, constraints) | L3 | ✅ Current | S10 |
| [S25_UI_Specs.md](specifications/S25_UI_Specs.md) | UI design system, screen layouts | L3 | ✅ Current | S15, S16, R09 |
| [S30_physical_specs.md](specifications/S30_physical_specs.md) | Stack decisions, project structure, deployment | L4 — Physical | ✅ Current | S20, S16 |
| [S35_semantic_layer.md](specifications/S35_semantic_layer.md) | Query patterns, semantic abstraction | L4 | ✅ Current | S20 |
| [S60_frontend_backend_separation.md](specifications/S60_frontend_backend_separation.md) | SPA migration plan (SEP-0 → SEP-4) | L4 | ✅ Current | S30 |
| [S65_brand_theme.md](specifications/S65_brand_theme.md) | Corporate visual identity, CSS variables | L4 | ✅ Current | S25 |
| [S70_workflow_engine_v3.md](specifications/S70_workflow_engine_v3.md) | Canonical workflow spec (engine, ECO optimizations, subprocess/assignment, runtime governance) | L3 + L4 | ✅ Current | S16, S20 |
| [S74_meeting_action_topic_inheritance.md](specifications/S74_meeting_action_topic_inheritance.md) | Meeting action category inheritance (pre-populate up to 2 categories) | L3 | ✅ Current | S05, S16, S25, S80 |
| [S75_workflow_ui_react_flow_update.md](specifications/S75_workflow_ui_react_flow_update.md) | Detailed workflow builder UI migration to React Flow: layout, interactions, serialization, validation, testing | L3 + L4 | ✅ Current | S70, S80 |
| [S80_react_frontend_architecture.md](specifications/S80_react_frontend_architecture.md) | React SPA as-built architecture reference | L4 | ✅ Current | S60 |
| [S90_SOP_Main_User_Flows.md](specifications/S90_SOP_Main_User_Flows.md) | Main user-flow SOP for meetings, actions, decisions, workflow, and admin operations | L4 | ✅ Current | S16, S80 |

---

## Archived

| File | Original ID | Reason | Date Archived |
|------|------------|--------|--------------|
| [R10_workflow_engine.md](archived/R10_workflow_engine.md) | R10 | Superseded by R16 + S70 (V2/V3 workflow) | 2026-02 |
| [S40_generation_plan.md](archived/S40_generation_plan.md) | S40 | Replaced by `CODE_GENERATION_PLAN.md` | 2026-02 |
| [R12_performance_optimisation.md](archived/R12_performance_optimisation.md) | R12 | 100% HTMX/Jinja2 content — retired in SEP-4 | 2026-03 |
| [S45_performance_optimisation.md](archived/S45_performance_optimisation.md) | S45 | 100% HTMX/Jinja2 content — retired in SEP-4 | 2026-03 |

---

## Dependency Graph

```
I00_intent.md (strategic intent)
└── R00_initial_vision.md (project vision)
    ├── R01_entities.md ──→ S05 ──→ S10 ──→ S11 ──→ S15 ──→ S16
    │   ├── R02_action_lifecycle.md          S10 ──→ S20 (DDL)
    │   ├── R03_assignment_workflow.md       S15 ──→ S25 (UI)
    │   ├── R04_notifications.md             S16 ──→ S30 (stack)
    │   ├── R05_dashboards_reporting.md      S20 ──→ S35 (queries)
    │   └── R07_data_import.md
    ├── R06_security.md
    ├── R08_taxonomy.md
    ├── R09_ui_content.md ──→ S25, S65
    ├── R16_workflow_app_extension.md ──→ S70, S75
    └── R17_meeting_decisions.md (planned)
        
    S60 (separation plan) ──→ S80 (React as-built)
```
