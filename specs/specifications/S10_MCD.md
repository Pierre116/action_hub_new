# ActionHub — Conceptual Data Model (MCD)

> **Level**: L1 — Conceptual  
> **Merise Phase**: Modèle Conceptuel des Données  
> **Source**: S05_data_dictionary.md, R01_entities.md  
> **Purpose**: Define entities and their relationships without implementation details (no FKs, no types)

---

## 1. Entity Inventory

| Entity | Key Fields | Cardinality | Phase |
|--------|------------|-------------|-------|
| **ACTION** | ACT_ID, ACT_REF, ACT_TITLE, ACT_STATUS, ACT_PRIORITY, ACT_DEADLINE, ACT_SOURCE, ACT_MTG_INST_ID, ACT_TOP_ID, ACT_SECONDARY_TOP_ID | High (~500+) | MVP |
| **USER** | USR_ID, USR_USERNAME, USR_DISPLAY, USR_ROLE | Low (<50) | MVP |
| **TEAM** | TEA_ID, TEA_NAME_EN, TEA_NAME_CN, TEA_CODE | Fixed (12) | MVP |
| **CATEGORY** | TOP_ID, TOP_NAME_EN, TOP_NAME_CN | Medium | MVP |
| **ASSIGNMENT** | ASG_ID, ASG_ROLE, ASG_STATUS | High | MVP |
| **ACTION_HISTORY** | AHI_ID, AHI_FIELD, AHI_CHG_TYPE, AHI_CHG_DATE | Very High | MVP |
| **PRIORITY_LEVEL** | — | Fixed (4) | MVP (enum) |
| **ESCALATION_LEVEL** | — | Fixed (3) | MVP (enum) |
| **IMPORT_LOG** | IML_ID, IML_FILE, IML_VERSION, IML_STATUS | Low | MVP |
| **SUB_ACTION** | SAC_ID, SAC_TITLE, SAC_STATUS | High | V1.1 |
| **ACTION_COMMENT** | — | Very High | V1.1 |
| **TAG** | TAG_ID, TAG_NAME | Medium | V1.1 |
| **MEETING_SUMMARY** | MTG_ID, MTG_TITLE, MTG_DATE | Medium | V1.1 |
| **NOTIFICATION_LOG** | NTL_ID, NTL_EVENT, NTL_SENT | Very High | V1.1 |
| **AUDIT_LOG** | AUD_ID, AUD_EVENT, AUD_TIMESTAMP | Very High | V1.1 |
| **WORKFLOW_TEMPLATE** | WFT_ID, WFT_NAME_EN, WFT_GRAPH | Low (~10–20) | V2.0 |
| **WORKFLOW_INSTANCE** | WFI_ID, WFI_STATUS, WFI_STARTED_AT | Medium (~100s) | V2.0 |
| **WORKFLOW_STEP_INSTANCE** | WSI_ID, WSI_STEP_KEY, WSI_STATUS | High | V2.0 |
| **WORKFLOW_STEP_FIELD_VALUE** | SFV_ID, SFV_FIELD_KEY, SFV_VALUE | High | V2.0 |
| **WORKFLOW_APPROVAL** | WAP_ID, WAP_DECISION, WAP_DECIDED_AT | Medium | V2.1 |
| **MEETING_DECISION** | MDC_ID, MDC_TITLE, MDC_STATUS, MDC_DECIDED_AT | Medium | V3.5 |

---

## 2. Relationships

| From | Verb | To | Cardinality | Business Rule | Phase |
|------|------|----|-------------|---------------|-------|
| TEAM | includes | USER | N:M (via USER_TEAM) | A user belongs to 1..N teams | MVP |
| USER | creates | ACTION | 1:N | A user creates 0..N actions | MVP |
| TEAM | classifies | ACTION | 0..1:N | An action optionally belongs to 1 team | MVP |
| CATEGORY | classifies (primary) | ACTION | 1:N | An action has exactly 1 primary category | MVP |
| CATEGORY | classifies (secondary) | ACTION | 0..1:N | An action optionally has 1 secondary category (max 2 total) | v2.14 |
| USER | is assigned to | ACTION | N:M (via ASSIGNMENT) | Many-to-many through ASSIGNMENT | MVP |
| ACTION | has | ASSIGNMENT | 1:N | An action has 1..N assignments | MVP |
| USER | has | ASSIGNMENT | 1:N | A user has 0..N assignments | MVP |
| ACTION | logs | ACTION_HISTORY | 1:N | Every action change creates a history entry | MVP |
| USER | performs | ACTION_HISTORY | 1:N | A user causes 0..N history entries | MVP |
| USER | runs | IMPORT_LOG | 1:N | An admin runs 0..N imports | MVP |
| ACTION | receives | ACTION_COMMENT | 1:N | An action has 0..N comments | V1.1 |
| USER | writes | ACTION_COMMENT | 1:N | A user writes 0..N comments | V1.1 |
| ACTION | tagged with | TAG | N:M (via ACTION_TAG) | Many-to-many, max 10 tags per action | V1.1 |
| MEETING_SUMMARY | spawns | ACTION | 1:N | A meeting can generate 0..N actions | V1.1 |
| USER | uploads | MEETING_SUMMARY | 1:N | A user uploads 0..N meeting summaries | V1.1 |
| USER | receives | NOTIFICATION_LOG | 1:N | A user receives 0..N notifications | V1.1 |
| ACTION | triggers | NOTIFICATION_LOG | 1:N | An action triggers 0..N notifications | V1.1 |
| USER | creates | WORKFLOW_TEMPLATE | 1:N | A user (Admin/TeamLead) creates 0..N workflow templates | V2.0 |
| WORKFLOW_TEMPLATE | instantiates | WORKFLOW_INSTANCE | 1:N | A template has 0..N running instances | V2.0 |
| ACTION | may support | WORKFLOW_INSTANCE | 1:0..1 | A linked action may have at most 1 workflow instance; request instances may have no bound action | V2.0 |
| WORKFLOW_INSTANCE | contains | WORKFLOW_STEP_INSTANCE | 1:N | An instance has 1..N step instances | V2.0 |
| USER | is assigned to | WORKFLOW_STEP_INSTANCE | 1:N | A user is assigned to 0..N step instances | V2.0 |
| WORKFLOW_STEP_INSTANCE | has | WORKFLOW_STEP_FIELD_VALUE | 1:N | A step instance has 0..N field values | V2.0 |
| USER | fills | WORKFLOW_STEP_FIELD_VALUE | 1:N | A user fills 0..N field values | V2.0 |
| WORKFLOW_STEP_INSTANCE | receives | WORKFLOW_APPROVAL | 1:N | An approval gate has 1..N approval records | V2.1 |
| USER | approves | WORKFLOW_APPROVAL | 1:N | A user makes 0..N approval decisions | V2.1 |
| MEETING_INSTANCE | records | MEETING_DECISION | 1:N | A meeting has 0..N decisions | V3.5 |
| USER | creates | MEETING_DECISION | 1:N | A user (meeting organizer) creates 0..N decisions | V3.5 |
| MEETING_DECISION | links to | ACTION | N:0..1 | A decision optionally links to 1 action; an action can be referenced by 0..N decisions | V3.5 |
| CATEGORY | classifies | MEETING_INSTANCE | 0..2:N | A meeting may belong to 0..2 categories | V3.8 |
| MEETING_DECISION | classified by | CATEGORY | N:0..2 | A decision optionally belongs to up to 2 categories | V3.5 |

---

## 3. Entity-Relationship Diagram (ASCII)

```
               ┌─────────┐ ┌─────────┐  ┌─────────┐
               │  TEAM   │ │CATEGORY │  │  USER   │
               │(12 seed)│ │         │  │  (<50)  │
               └────┬────┘ └────┬────┘  └────┬────┘
                    │           │             │
                    └─────┬─────┘             │
                          │                   │
                          ▼                   │
                    ┌───────────┐              │
                    │  ACTION   │◄─────────────┘ creates
                    │  (500+)   │
                    └─────┬─────┘
           ┌──────────────┼──────────────────┐
           │              │                  │
           ▼              ▼                  ▼
     ┌───────────┐  ┌───────────────┐  ┌──────────┐
     │ASSIGNMENT │  │ACTION_HISTORY │  │ CATEGORY │
     │  (N:M)    │  │   (audit)     │  │ (8 seed) │
     └───────────┘  └───────────────┘  └──────────┘
           │
           ▼
     ┌───────────┐
     │   USER    │ (assignee)
     └───────────┘

     V1.1 Extensions:
     ACTION ──1:N──► SUB_ACTION
     ACTION ──1:N──► ACTION_COMMENT ◄──N:1── USER
     ACTION ──N:M──► TAG (via ACTION_TAG)
     ACTION ──N:1──► MEETING_SUMMARY ◄──N:1── USER

     V2 Extensions (Workflow — D167–D180):
     USER ──1:N──► WORKFLOW_TEMPLATE (creates)
     WORKFLOW_TEMPLATE ──1:N──► WORKFLOW_INSTANCE
      ACTION ──1:0..1──► WORKFLOW_INSTANCE (optional link; UNIQUE when present)
     WORKFLOW_INSTANCE ──1:N──► WORKFLOW_STEP_INSTANCE
     USER ──1:N──► WORKFLOW_STEP_INSTANCE (assignee)
     WORKFLOW_STEP_INSTANCE ──1:N──► WORKFLOW_STEP_FIELD_VALUE
     WORKFLOW_STEP_INSTANCE ──1:N──► WORKFLOW_APPROVAL (V2.1)
```

---

## 4. Business Rules (Conceptual)

### 4.1 Action Rules

| # | Rule | Constraint |
|---|------|-----------|
| BR01 | Every Action must have exactly 1 Lead assignment | Mandatory relationship |
| BR02 | An Action must belong to exactly 1 Team | Mandatory classification |
| BR03 | Done and Cancelled are terminal states — no outgoing transitions | State machine integrity |
| BR04 | An Action's deadline cannot be in the past at creation | Temporal constraint |
| BR05 | Reference code (ACT_REF) is auto-generated and immutable | Identity constraint |

### 4.2 Assignment Rules

| # | Rule | Constraint |
|---|------|-----------|
| BR08 | Every Action has exactly 1 Lead at all times | Cardinality constraint |
| BR09 | ~~Role separation constraints on action assignments~~ — **withdrawn** under lead-based action control; legacy assignment-role combinations are compatibility-only | ~~Role separation~~ — compatibility note |
| BR10 | Assignments can cross team boundaries | No team isolation |
| BR11 | All assignments start as Pending — assignee must explicitly accept | Assignment rule |
| BR12 | V1.1: Declined delegate cannot be re-assigned to same action unless they accept | Reassignment guard |

### 4.3 Taxonomy Rules

| # | Rule | Constraint |
|---|------|-----------|
| BR13 | All taxonomy items use soft-delete (is_active = false) | Referential integrity |
| BR14 | Cannot hard-delete Team if it has members | Cascade protection |
| BR15 | Cannot hard-delete Team if it has Categories | Cascade protection |
| BR16 | Tags are case-insensitive, normalized to lowercase | Uniqueness constraint |
| BR17 | Maximum 10 tags per Action | V1.1 — cardinality limit |

### 4.4 User Rules

| # | Rule | Constraint |
|---|------|-----------|
| BR18 | Action and meeting visibility is scoped (creator/assignee/participant/meeting-creator/team-lead rules; private content masked where required) | Visibility policy (R19, R20) |
| BR19 | Username must be unique | Identity constraint |
| BR20 | Account lockout after 5 failed logins in 15 minutes | Security constraint |

### 4.5 Import Rules

| # | Rule | Constraint |
|---|------|-----------|
| BR21 | Import is one-time seed, not recurring sync | Operational constraint (D96) |
| BR22 | Import creates new records only, never modifies existing | Non-destructive (D97) |
| BR23 | Import batch can be rolled back (delete by import_log_id) | Reversibility (D98) |
| BR24 | Duplicate detection: exact title + team match in MVP | Dedup rule (D163) |

### 4.6 Workflow Rules (V2 — D167–D180)

| # | Rule | Constraint |
|---|------|-----------|
| BR25 | A WorkflowInstance may optionally reference 1 Action (`wfi_action_id UNIQUE` when non-null); standalone request workflows may run without a bound action | Runtime decoupling |
| BR26 | Existing-action workflow start is compatibility-only; the primary runtime model is workflow-area launch and workbench-driven execution | Process-first model |
| BR27 | Workflow template graph stored as JSON in `wft_graph`; steps, transitions, triggers, fields are not separate entities | D176/O3 |
| BR28 | In-flight instances stay on their original template version; new instances use latest active version | Versioning rule |
| BR29 | A Join step auto-advances only when ALL incoming parallel branches are Completed | D172: parallel paths |
| BR30 | Parallel join uses `BEGIN IMMEDIATE` to prevent race conditions (SQLite) | D179 |
| BR31 | An Approval gate step requires at least 1 approval decision before the transition fires | Gate rule |
| BR32 | Approval gate decisions are evaluated against active approver assignment rules | D170 |
| BR33 | SLA deadline computed as `wsi_entered_at + sla_hours` (business hours or calendar per config) | D174 |
| BR34 | `act_status` stays canonical for workflow-bound actions; display_status is derived from current step name | D173 |
| BR35 | Step form field values from earlier steps are visible (read-only) to later steps | Data flow between steps |
| BR36 | Only Admin and TeamLead can create/edit workflow templates | D169 |
| BR37 | TeamLead can only bind workflow templates to their own team | D169 scoping |
### Unified Action Management Relationships

- ACTION ↔ MEETING_SUMMARY (via ACT_MTG_INST_ID)
- ACTION ↔ WORKFLOW_INSTANCE (via optional `WFI_ACTION_ID` on workflow runtime)
- ACTION ↔ CATEGORY (via ACT_TOP_ID, ACT_SECONDARY_TOP_ID)
