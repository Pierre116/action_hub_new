# ActionHub — Agent Framework (V3+ Vision)

> **Status**: Requirements-level specification — **FUTURE / NOT IN V1 SCOPE**  
> **Depends on**: `R16_workflow_app_extension.md` (workflow foundation), `R04_notifications.md` (notification system)  
> **Decisions**: D131–D140 in `DECISIONS.md`  
> **Consumed by**: V3+ planning only

---

## §1 Overview

The Agent Framework extends ActionHub with autonomous software agents that monitor, analyze, and act on action data. Agents operate within defined boundaries, executing rules-based or AI-powered tasks to reduce manual follow-up overhead and improve organizational responsiveness.

**This is V3+ scope** — V2 (Workflow Engine) must be stable before agents are introduced. V1 design should not block agent integration.

---

## §2 Architectural Preparation

### §2.1 V1 Design Hooks for Agents (D131)

| V1 Element | Agent-Ready Design |
|------------|-------------------|
| Event system | All state changes emit events (ActionHistory) that agents can subscribe to |
| API layer | RESTful APIs that agents can call (create, update, assign, notify) |
| Notification engine | Generic enough to support agent-generated notifications |
| Audit trail | All agent actions logged with `performed_by = agent_{name}` |
| User model | Support for "system user" / "agent user" accounts (D131) |

### §2.2 Agent User Account Pattern

```python
# V1: define a system user type for future agent accounts
USER_TYPES = ["human", "agent"]  # V1 only uses "human"

# V3: agent accounts
# - Cannot log in via UI
# - Identified in audit trail
# - Subject to rate limits
# - Scoped to specific action permissions
```

---

## §3 V3 Agent Catalog (D132)

### §3.1 Rules-Based Agents (D133)

| Agent | Function | Trigger |
|-------|----------|---------|
| **Deadline Monitor** | Detect approaching/overdue deadlines, send reminders, escalate | Daily cron job |
| **Assignment Monitor** | Detect unresponded assignments, remind, escalate to Lead | Hourly check |
| **Stale Action Detector** | Identify actions with no updates for N days, notify Lead | Weekly scan |
| **Dependency Resolver** | When blocking action completes, auto-notify blocked actions and suggest status change | Event: status → Done |
| **Escalation Agent** | Apply auto-escalation rules (per R02 §5.2), manage de-escalation | Event: overdue detected |
| **Report Agent** | Execute scheduled reports and deliver via email | Cron per schedule |

### §3.2 AI-Powered Agents (D134)

| Agent | Function | Model |
|-------|----------|-------|
| **Duplicate Detector** | Scan new actions for similarity with existing open actions | Text embedding + cosine similarity |
| **Smart Assign** | Suggest assignees based on category, workload, and historical performance | Rule-based + optional ML |
| **Risk Predictor** | Flag actions likely to miss deadline based on historical patterns | Classification model |
| **Meeting Summarizer** | Extract action items from uploaded meeting minutes (Word) | LLM (GPT/DeepSeek) |
| **Translation Agent** | Auto-translate action titles/descriptions EN↔CN | LLM or MT API |

---

## §4 Agent Architecture (D135)

### §4.1 Agent Lifecycle

```
Registered → Configured → Active → [Running / Idle] → Disabled → Archived
```

### §4.2 Agent Components

```
┌─────────────────────────────────────────┐
│              Agent Framework             │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Event    │  │ Agent    │  │ Agent │ │
│  │ Bus      │──│ Registry │──│ Runner│ │
│  │ (subscribe│  │ (config) │  │ (exec)│ │
│  │  to events│  └──────────┘  └───────┘ │
│  └──────────┘                           │
│       │          ┌──────────┐           │
│       └──────────│ Agent    │           │
│                  │ Logger   │           │
│                  │ (audit)  │           │
│                  └──────────┘           │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │          ActionHub APIs          │   │
│  │  (actions, assignments, notifs)  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### §4.3 Agent Configuration (D136)

Each agent has a configuration:

| Field | Type | Description |
|-------|------|-------------|
| agent_id | VARCHAR(50) | Unique identifier |
| display_name | VARCHAR(100) | Bilingual name |
| type | ENUM | rules / ai |
| schedule | CRON | Execution schedule (or event-driven) |
| event_triggers | JSON | List of events that trigger this agent |
| parameters | JSON | Agent-specific config (thresholds, etc.) |
| is_active | BOOLEAN | Enable/disable |
| max_actions_per_run | INT | Rate limit |
| created_by | FK → User | Admin who configured it |

---

## §5 Agent Boundaries & Safety (D137)

| Rule | Enforcement |
|------|-------------|
| Agents cannot delete actions | API restriction |
| Agents cannot transfer action Lead autonomously | Lead updates require explicit human approval |
| Agent actions require human confirmation for: | Priority upgrade, escalation to WAR, action cancellation |
| Rate limiting | Max N actions per agent per hour |
| Audit trail | Every agent action logged with agent_id |
| Kill switch | Admin can disable any agent instantly |
| Dry-run mode | Test agent logic without executing side effects |

---

## §6 Agent Dashboard (D138)

| Section | Content |
|---------|---------|
| Agent overview | List of all agents with status, last run, next run |
| Execution log | Chronological list of agent actions |
| Impact metrics | Actions processed, notifications sent, escalations triggered per agent |
| Configuration | Edit agent parameters, enable/disable |
| Alerts | Agent errors, rate limit breaches, unexpected behavior |

---

## §7 Migration Path (D139–D140)

| Phase | Deliverable |
|-------|-------------|
| V1 | Event-driven ActionHistory; system user account type defined (D131) |
| V2 | Scheduled jobs for reports (cron); Deadline Monitor as first "proto-agent" |
| V3 alpha | Agent framework with 3 rules-based agents (Deadline, Assignment, Stale) |
| V3 beta | AI-powered agents: Duplicate Detector, Smart Assign |
| V3 GA | Full agent dashboard, self-service configuration, AI agents with LLM |
