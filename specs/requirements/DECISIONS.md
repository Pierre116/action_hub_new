# ActionHub — Decision Log

> **Status**: Living document — append-only  
> **Rule**: D-numbers are globally unique and immutable once assigned. Amendments create new D-numbers.  
> **Total**: 214 decisions (D1–D214)

---

## Table of Contents

| Domain | Decisions | Range |
|--------|-----------|-------|
| [Foundation & Deployment](#foundation--deployment) | Project name, platform, DB, concurrency, phasing | D1–D15 |
| [Action Lifecycle](#action-lifecycle) | Statuses, priorities, SLA, dependencies, escalation | D16–D38 |
| [Assignment Workflow](#assignment-workflow) | Roles, accept/decline, reassignment, audit | D39–D50 |
| [Notifications](#notifications) | Bell, email, reminders, preferences | D51–D60 |
| [Dashboards & Reporting](#dashboards--reporting) | KPIs, charts, export, scheduled reports | D61–D75 |
| [Security & Auth](#security--auth) | Auth, RBAC, sessions/JWT, CSRF, audit | D76–D88 |
| [Data Import](#data-import) | Excel import, dedup, mapping, rollback | D89–D98 |
| [Taxonomy](#taxonomy) | Teams, categories, tags, soft-delete | D99–D108 |
| [UI & Content](#ui--content) | i18n, navigation, pages, browser support | D109–D120 |
| [Workflow V1/V2](#workflow-v1v2) | Status transitions, templates, routing, visual builder | D121–D130 |
| [Agent Framework](#agent-framework) | Agent types, architecture, safety, dashboard | D131–D140 |
| [MVP Scoping](#mvp-scoping) | Deferrals, phasing, quick-capture, onboarding | D141–D166 |
| [Workflow V2 Extension](#workflow-v2-extension) | Standalone requests, fields, permissions, parallel | D167–D180 |
| [Workflow V3](#workflow-v3) | 3-phase lifecycle, gateways, service steps, timer, SLA | D181–D192 |
| [ECO Optimizations](#eco-optimizations) | Link fields, context fields, join modes, iteration limits | D193–D198 |
| [Subprocess & Assignment Rules](#subprocess--assignment-rules) | Subprocess steps, declarative assignment, round-robin | D199–D205 |
| [Taxonomy Consolidation](#taxonomy-consolidation) | Category rename, max-2 category attachments, Action Type removal | D211–D214 |

---

## Foundation & Deployment

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D1** | Project name: "ActionHub" | Elicitation Q&A | R00 |
| **D2** | Browser-based web app (not desktop or mobile-native) | Q18 | R00 |
| **D3** | Local Windows server deployment (on-premise) | Q19 | R00 |
| **D4** | SQLite database (single-file, zero-config, WAL mode) — replaces MySQL for simplified deployment | Q19 + Round 3 | R00 |
| **D5** | Day 1: simple username/password auth; V1.1: Windows AD/LDAP | Q17 + Round 3 | R00, R06 |
| **D6** | Bilingual UI: Chinese + English toggle | Q20 | R00 |
| **D7** | **Retired** — legacy global-visibility assumption removed; visibility is scoped by creator/assignment/meeting/team-lead rules per R19 and R20 | Q18 (round 2) | R20 |
| **D8** | Online-only — server must be LAN-accessible | Q20 (round 2) | R00 |
| **D9** | <10 concurrent users | Q2 | R00 |
| **D10** | 12 teams: Facility, IE, CI, Quality, HP, Warehouse, Logistic, Sourcing, Procurement, MM, ESL, Planning | Q1 + Round 3 | R00, R08 |
| **D11** | Shared action pool (no per-team databases) | Q4 | R00 |
| **D12** | Workload KPIs are count-based (no effort/hours tracking) | Q12 (round 2) | R05 |
| **D13** | Excel is primary export format (no PDF/Word for V1) | Q15 (round 2) | R05 |
| **D14** | Future evolution toward workflow engine + agent framework | Q20 (round 2) | R10, R11 |
| **D15** | Scheduled reports with auto-email delivery | Q16 (round 2) | R05 |

## Action Lifecycle

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D16** | All taxonomy (Team, Team, Category, Category) admin-configurable | Q9 (round 2) | R08 |
| **D17** | Free-form tagging system in addition to structured taxonomy | Q10 (round 2) | R08 |
| **D18** | Priority levels: Critical, High, Medium, Low | Q9 | R02 |
| **D19** | Escalation levels: Normal, Escalated, WAR (from v4 红单 pattern) | Q9 | R02 |
| **D20** | **Retired** — action responsibility is lead-based, not RACI role-based | Q5 (round 2) | R03 |
| **D21** | Action dependencies supported: blocks + related_to | Q11 (round 2) | R02 |
| **D22** | RBAC roles: Admin, TeamLead, Member, ReadOnly | Q3 | R06 |
| **D23** | User preferred language stored in profile | Implied by D6 | R01, R09 |
| **D24** | Direct completion (skip review) allowed for simple actions | Design decision | R02 |
| **D25** | Done and Cancelled are terminal states — no reopening | Design decision | R02 |
| **D26** | Default priority for new actions: Medium | Design decision | R02 |
| **D27** | Default owner for new actions is the creator | Design decision | R02 |
| **D28** | **Retired** — legacy action-hierarchy deadline policy removed from active scope | Design decision | R02 |
| **D29** | **Retired** — legacy parent-child closure dependency removed from active scope | Design decision | R02 |
| **D30** | SLA by priority: Critical=3d, High=7d, Medium=14d, Low=30d | Design decision | R02 |
| **D31** | Priority upgrade triggers notification to all assignees | Design decision | R02 |
| **D32** | Auto-escalation triggers based on overdue days + priority | Design decision | R02 |
| **D33** | Two dependency types: blocks (enforced), related_to (informational) | Design decision | R02 |
| **D34** | Circular dependency detection — system rejects cycles | Design decision | R02 |
| **D35** | Activity stream displayed newest-first | Design decision | R02 |
| **D36** | **Retired** — legacy hierarchy-based closure prerequisite removed from active scope | Design decision | R02 |
| **D37** | Done actions cannot be reopened; create new action with related_to link | Design decision | R02 |
| **D38** | Bulk operations create individual audit entries per action | Design decision | R02 |

## Assignment Workflow

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D39** | **Retired** — multi-role action assignment model removed from active policy | Q5 (round 2) | R03 |
| **D40** | Exactly 1 owner per action | Design decision | R03 |
| **D41** | Default owner = action creator (can be changed when policy allows) | Design decision | R03 |
| **D42** | Delegates must explicitly accept or decline assignments | Q6 (round 2) | R03 |
| **D43** | System suggests alternative assignees when delegate declines | Q7 (round 2) | R03 |
| **D44** | 48h acceptance window; 24h reminder; no auto-accept | Design decision | R03 |
| **D45** | Reassignment creates new Assignment record; old one marked Reassigned | Design decision | R03 |
| **D46** | Owner transfer is restricted by policy and must be audit logged | Design decision | R03 |
| **D47** | Legacy delegate acceptance rule retired with lead-based model | Design decision | R03 |
| **D48** | Legacy participant self-subscribe rule retired with lead-based model | Design decision | R03 |
| **D49** | Audit queries: assignment timeline, decline rate, response time, workload history | Q8 (round 2) | R03 |
| **D50** | Edge cases for deactivated users: warn owner, prompt reassignment | Design decision | R03 |

## Notifications

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D51** | Comment notifications are user-configurable (on/off) | Design decision | R04 |
| **D52** | Deadline reminders: 3 days before + daily when overdue | Q13 | R04 |
| **D53** | Deadline-day notification sent in morning batch (08:00) | Design decision | R04 |
| **D54** | Assignment events are instant; deadline reminders are daily batch | Design decision | R04 |
| **D55** | No emails outside 08:00–18:00 local time; queued to next business morning | Design decision | R04 |
| **D56** | Email templates are bilingual (EN + CN in same email) | Implied by D6 | R04 |
| **D57** | Users can configure notification preferences in settings | Design decision | R04 |
| **D58** | All notifications logged (sent, read, failed status) | Design decision | R04 |
| **D59** | Failed emails retry 3 times with exponential backoff | Design decision | R04 |
| **D60** | Read notifications purged after 90 days; audit log kept 1 year | Design decision | R04 |

## Dashboards & Reporting

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D61** | Default landing page: Personal Dashboard | Design decision | R05 |
| **D62** | Workload distribution: bar chart of action count per user | D12 | R05 |
| **D63** | Completion trend: 12-week rolling line chart | Design decision | R05 |
| **D64** | Dual-axis trend: created vs completed over time | Q13 (round 2) | R05 |
| **D65** | Cross-team comparison chart for Admin/Management | Design decision | R05 |
| **D66** | Management dashboard: single-page executive summary | Q14 (round 2) | R05 |
| **D67** | KPIs: completion rate, overdue count/rate, avg completion time, on-time rate | Design decision | R05 |
| **D68** | Workload KPIs: actions per user, new/closed per period, net change, backlog | Design decision | R05 |
| **D69** | Assignment KPIs: acceptance rate, avg response time, reassignment rate | Design decision | R05 |
| **D70** | Report builder: select columns, filters, grouping, sorting, aggregation | Design decision | R05 |
| **D71** | 6 pre-built report templates | Design decision | R05 |
| **D72** | Excel export with bilingual headers, auto-filter, conditional formatting | D13 | R05 |
| **D73** | Scheduled reports: daily/weekly/monthly with email delivery | D15 | R05 |
| **D74** | Ad-hoc export: "Export to Excel" from any filtered view | Design decision | R05 |
| **D75** | Chart specs: 7 chart types defined with axes and color scheme | Design decision | R05 |

## Security & Auth

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D76** | Authentication: Day 1 simple username/password (bcrypt); V1.1 LDAP bind against Windows AD | Q17 + Round 3 | R06 |
| **D77** | Session timeout: 8 hours | Design decision | R06 |
| **D78** | Account lockout after 5 failed logins in 15 minutes (30 min lockout) | Design decision | R06 |
| **D79** | AD sync: real-time on login + nightly batch | Design decision | R06 |
| **D80** | New AD users auto-created with role = Member on first login | Design decision | R06 |
| **D81** | Four roles: Admin, TeamLead, Member, ReadOnly | D22 | R06 |
| **D82** | Full permission matrix defined (18 operations × 4 roles) | Design decision | R06 |
| **D83** | **Retired** — replaced by scoped runtime visibility policy (see R19 and R20) | D7 | R20 |
| **D84** | Server-side sessions with HttpOnly, Secure, SameSite cookies | Design decision | R06 |
| **D85** | CSRF protection via framework middleware | Design decision | R06 |
| **D86** | Audit logging: auth events, data changes, admin ops, report access | Design decision | R06 |
| **D87** | Audit logs retained 3 years minimum, read-only | Design decision | R06 |
| **D88** | HTTPS recommended; SQLite file permissions; uploads outside webroot | Design decision | R06 |

## Data Import

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D89** | User name resolution: exact match → partial match → unresolved (admin maps) | Design decision | R07 |
| **D90** | Import workflow: upload → detect version → preview → resolve mappings → confirm | Design decision | R07 |
| **D91** | Auto-detect Excel version by sheet name and header pattern | Design decision | R07 |
| **D92** | Data quality: skip empty titles, import null deadlines with flag, normalize statuses | Design decision | R07 |
| **D93** | Duplicate detection: title similarity + owner + deadline + team scoring | Design decision | R07 |
| **D94** | Import log entity with full stats and warning details | Design decision | R07 |
| **D95** | Post-import validation: review, resolve owners, merge duplicates, assign taxonomy | Design decision | R07 |
| **D96** | Import is one-time seed, not recurring sync | Q6 | R07 |
| **D97** | Import creates new records only, never overwrites existing | Design decision | R07 |
| **D98** | Rollback: delete all records from a specific import batch | Design decision | R07 |

## Taxonomy

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D99** | 12 seed teams: FAC, IE, CI, QA, HP, WH, LOG, SRC, PROC, MM, ESL, PLAN | Stakeholder input | R08 |
| **D100** | Teams are children of teams, admin-configurable | Design decision | R08 |
| **D101** | Categories can be team-level or team-level | Design decision | R08 |
| **D102** | Categories are a flat orthogonal dimension (8 seed values) | Design decision | R08 |
| **D103** | Tags: free-form, case-insensitive, auto-complete, admin-curated | D17 | R08 |
| **D104** | Maximum 10 tags per action | Design decision | R08 |
| **D105** | Taxonomy admin: tree view, drag-drop reorder, bilingual fields, usage count | Design decision | R08 |
| **D106** | Tag admin: merge, rename, deactivate, cleanup unused | Design decision | R08 |
| **D107** | All taxonomy uses soft-delete (is_active flag) | Design decision | R08 |
| **D108** | Referential integrity: block delete if children exist; soft-delete for referenced items | Design decision | R08 |

## UI & Content

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D109** | Full i18n: UI chrome translated, user content stored as-is | D6 | R09 |
| **D110** | Date format: EN = YYYY-MM-DD, CN = YYYY年MM月DD日 | Design decision | R09 |
| **D111** | Sidebar navigation with collapsible sections | Design decision | R09 |
| **D112** | Action list: paginated data table with sort/filter/search/export/bulk-select | Design decision | R09 |
| **D113** | **Retired** — legacy Action detail hierarchy panel removed from active scope | Design decision | R09 |
| **D114** | Action form: cascading dropdowns (dept→team→category), user search, tag autocomplete | Design decision | R09 |
| **D115** | Desktop-first; tablet/mobile functional but not optimized in V1 | Design decision | R09 |
| **D116** | Color palette defined: 8 colors for statuses + priorities | Design decision | R09 |
| **D117** | 11 reusable UI components defined | Design decision | R09 |
| **D118** | Page load target: <2s on LAN | Design decision | R09 |
| **D119** | Browser support: Chrome 90+, Edge 90+ | Design decision | R09 |
| **D120** | Dashboard views printable with CSS print styles | Design decision | R09 |

## Workflow V1/V2

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D121** | V1: Status transitions stored in config table (not hardcoded) for future workflow extensibility | D14 | R10 |
| **D122** | Status transition table pattern with workflow_id column (NULL = default) | D121 | R10 |
| **D123** | V2 workflow concepts: templates, steps, transitions, gates, triggers, SLAs | D14 | R10 |
| **D124** | Workflow routing: sequential, conditional, parallel, loop-back, sub-workflow | D14 | R10 |
| **D125** | V2 approval gates: single, any-of-N, all-of-N, majority, hierarchical | D14 | R10 |
| **D126** | V2 automation triggers on step events | D14 | R10 |
| **D127** | V2 visual workflow builder UI | D14 | R10 |
| **D128** | Migration: V1→V2 via transition table + flexible ActionHistory | D14 | R10 |
| **D129** | V2 alpha: 2–3 hardcoded workflow templates | D14 | R10 |
| **D130** | V2 GA: full self-service workflow configuration | D14 | R10 |

## Agent Framework

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D131** | V1: support "agent" user type in User model (inactive until V3) | D14 | R11 |
| **D132** | V3 agent catalog: 6 rules-based + 5 AI-powered agents defined | D14 | R11 |
| **D133** | Rules-based agents: Deadline, Assignment, Stale, Dependency, Escalation, Report | D14 | R11 |
| **D134** | AI agents: Duplicate Detector, Smart Assign, Risk Predictor, Meeting Summarizer, Translator | D14 | R11 |
| **D135** | Agent architecture: Event Bus + Registry + Runner + Logger | D14 | R11 |
| **D136** | Agent configuration: per-agent schedule, triggers, parameters, rate limits | D14 | R11 |
| **D137** | Agent safety: no delete, no Lead assign, human confirmation for escalation, kill switch | D14 | R11 |
| **D138** | Agent dashboard: status, execution log, impact metrics, configuration | D14 | R11 |
| **D139** | V2→V3: scheduled jobs as proto-agents; Deadline Monitor first | D14 | R11 |
| **D140** | V3 GA: full agent dashboard + AI agents with LLM | D14 | R11 |

## MVP Scoping

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D141** | V1 MVP target: 1.5-day sprint (Day 1: core CRUD + import + personal dashboard; Day 2 AM: dept dashboard + export + deploy) | Round 4 | R00 |
| **D142** | Meeting minutes upload deferred to V1.1 (not critical for MVP adoption; actions are the core loop) | Round 4 | R00, R01 |
| **D143** | Database changed from MySQL to SQLite (WAL mode) for zero-config deployment | Round 3 | R00, R01, R06, R07 |
| **D144** | MVP uses 10 pages only (Login, Personal Dashboard, Action List, Detail, New, Edit, Dept Dashboard, Admin Users, Admin Import, Quick-capture modal) | Round 4 | R09 |
| **D145** | Accept/decline assignment workflow deferred to V1.1; MVP uses auto-accept on assign | Round 4 | R03 |
| **D146** | Email notifications deferred to V1.1; MVP uses passive visual indicators (red/amber on dashboard) | Round 4 | R04 |
| **D147** | **Retired** — legacy hierarchy feature removed from active roadmap/spec scope | Round 4 | R01, R02 |
| **D148** | Action dependencies (blocks/related_to) deferred to V1.2 | Round 4 | R02 |
| **D149** | Auto-escalation triggers deferred to V1.2; MVP supports manual escalation_level field | Round 4 | R02 |
| **D150** | Bulk operations deferred to V1.1 | Round 4 | R02 |
| **D151** | Full ActionComment entity deferred to V1.1; MVP uses Action.last_comment text field | Round 4 | R01, R02 |
| **D152** | Tags (free-form labels) deferred to V1.1; MVP uses structured taxonomy only | Round 4 | R08 |
| **D153** | Team Dashboard and Management Dashboard deferred to V1.1 | Round 4 | R05 |
| **D154** | Report builder + scheduled reports deferred to V1.2; MVP has ad-hoc Excel export only | Round 4 | R05 |
| **D155** | Quick-capture: persistent "+" FAB on every page for frictionless action creation | Round 4 | R00, R09 |
| **D156** | Personal Dashboard = "Today" focus view: Overdue (red) + Due This Week (amber) + Recently Completed (green) | Round 4 | R05, R09 |
| **D157** | Inline status update: click status badge → dropdown → instant save (no page navigation) | Round 4 | R02, R09 |
| **D158** | First-login onboarding: 3-step tooltip tour ("Your actions" → "Filters" → "Quick capture +") | Round 4 | R09 |
| **D159** | Empty states show encouraging messages with CTAs, not blank screens | Round 4 | R09 |
| **D160** | Full RBAC (4 roles × 18 ops) deferred to V1.1; MVP uses binary Admin/Member check | Round 4 | R06 |
| **D161** | Status transition table (DB) deferred to V1.1; MVP uses Python dict (per R02 §3.2) | Round 4 | R10 |
| **D162** | Import priority: v3 + v4 first (largest datasets), then v1 + v2 | Round 4 | R07 |
| **D163** | Duplicate detection in MVP: exact title + team match only; fuzzy scoring in V1.1 | Round 4 | R07 |
| **D164** | Taxonomy seeded at deployment (SQL migration); admin tree view UI in V1.1 | Round 4 | R08 |
| **D165** | Three-phase release: MVP (1.5d) → V1.1 (Week 2, engagement) → V1.2 (Week 3-4, power features) before V2 | Round 4 | R00 |
| **D166** | Legacy role-combination assignment model retired; lead-based model is authoritative for action control | Design decision | R03 |

## Workflow V2 Extension

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D167** | Workflow supports both action-bound and standalone requests; standalone requests stored as `t_action` with `act_source = 'WorkflowRequest'` (no separate `t_process_request` table) — O2 | R16 Q1 + O2 | R16 |
| **D168** | Step form fields: text, dropdown, date, number, checkbox, checklist; **no file attachments** (security policy — drawing leakage risk) | R16 Q2 | R16 |
| **D169** | Workflow template builder permissions: Admin (full) + TeamLead (scoped to own team bindings); Member/ReadOnly view-only | R16 Q3 | R16 |
| **D170** | **Retired** — backup-approver feature removed from active schema/spec scope | R16 Q4 | R16 |
| **D171** | V2 notifications: in-app only; email deferred to V2.5 | R16 Q5 | R16 |
| **D172** | Parallel paths (fork/join) are a core feature; common in multi-team processes | R16 Q6 | R16 |
| **D173** | Workflow-bound actions show step name as display status; `act_status` stays canonical with computed `display_status` | R16 Q7 | R16 |
| **D174** | Dashboard primary metrics: completion rate + lead time; every step has SLA | R16 Q8 | R16 |
| **D175** | Pilot workflow: OT User Creation (5 teams, parallel path); hardcoded as Python dict first (O5) | R16 Q9 + O5 | R16 |
| **D176** | Workflow template graph stored as single JSON column `wft_graph` in `t_workflow_template`; runtime tables stay normalized — reduces 12 tables to 6 (O3) | R16 O3 | R16 |
| **D177** | Visual canvas builder uses Drawflow (MIT, 4 KB, vanilla JS, no build step) — fits Flask+Jinja2+HTMX stack; deferred to V2.4 (O1 + O4) | R16 O1+O4 | R16 |
| **D178** | V2 phasing: engine-first, canvas-later; V2.0-alpha (hardcoded pilot) → V2.0-beta (SLA) → V2.1 (approvals) → V2.2 (dashboard) → V2.3 (in-app editor) → V2.4 (canvas) → V2.5 (conditional routing + email) | R16 O1 | R16 |
| **D179** | SQLite `BEGIN IMMEDIATE` for parallel join race condition: check all parallel branches completed before advancing | R16 Risk R2 | R16 |
| **D180** | SLA monitoring via APScheduler (lightweight, in-process); no Celery/Redis needed for <10 users | R16 Risk R3 | R16 |

## Workflow V3

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D181** | Steps use 3-phase lifecycle: Pending → Accepted → Completed/Rejected. Explicit accept required before work begins. | V3 Q1 | S70 |
| **D182** | Rejection bounces step back to previous step assignee with mandatory reason; previous assignee can escalate to workflow creator | V3 Q2 | S70 |
| **D183** | After step completion, user sees full read-only timeline + can override next step assignee from eligible-user dropdown | V3 Q3 | S70 |
| **D184** | Runtime assignee resolution via dropdown of eligible team members; completing user may override template default | V3 Q4 | S70 |
| **D185** | Gateway decision tables evaluate prior step field values from `t_workflow_step_field_value`; field values take precedence | V3 Q5 | S70 |
| **D186** | Service steps execute registered Python callables from whitelist registry; on error: pause and notify workflow creator | V3 Q6 | S70 |
| **D187** | Multiple End steps allowed per graph; each End has distinct `outcome` label mapping to a specific `action_status` | V3 Q7 | S70 |
| **D188** | Timer steps auto-escalate to team lead and reassign; logged as `SLAEscalation` | V3 Q8 | S70 |
| **D189** | Step types expanded to 8: Task, Approval, Gateway, Service, Notification, Timer, Join, End | V3 Q9 | S70 |
| **D190** | Transition types: `normal`, `rejection`, `timeout`, `condition`; engine uses type to select correct path | V3 Q10 | S70 |
| **D192** | Graph validation: ≥1 End step (not exactly 1); decision table validation; service handler registry checks added | V3 Q12 | S70 |

## ECO Optimizations

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D193** | Add `link` field type to step fields. Renders as clickable URL; no file upload — references external storage only. Reject `javascript:`, `data:`, `file:` schemes. | ECO gap analysis | S71 |
| **D194** | Steps may declare `context_fields`: prior step field values displayed read-only above the step form. Engine populates from `t_workflow_step_field_value`. | ECO gap analysis | S71 |
| **D195** | Join step gains `mode` property: `all` (default) or `first_reject`. In `first_reject`, any incoming branch rejection cancels sibling branches and propagates rejection. | ECO gap analysis | S71 |
| **D196** | Rejection transitions may declare `max_iterations`. Engine tracks iteration count; when limit reached, step pauses and notifies workflow creator instead of looping. | ECO gap analysis | S71 |
| **D197** | `wsi_comment` accepted on all step completions (advance, accept), not only rejection. Optional for non-rejection actions. | ECO gap analysis | S71 |
| **D198** | Built-in ECO pilot template graph seeded via migration. 15 steps demonstrating all V3 + S71 features. Editable by admin. | ECO gap analysis | S71 |

## Subprocess & Assignment Rules

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D199** | New step type `Subprocess`: engine pauses parent step until child workflow instance reaches terminal state; child outcome + output fields propagated back. | B-1 | S72 |
| **D200** | Subprocess nesting depth limited to 1 (parent → child only, no grandchild). Validated at instantiation. | B-1 | S72 |
| **D201** | Declarative assignment rules in graph JSON. Five types: `static_user`, `role_in_team`, `prior_step_actor`, `workflow_creator`, `round_robin`. First match wins; fallback: workflow creator. | B-1 | S72 |
| **D202** | **Retired** — workflow step transfer branch removed from active schema/spec scope | B-1 | S72 |
| **D203** | **Retired** — eligibility rule for the removed transfer branch is retired | B-1 | S72 |
| **D204** | Round-robin tracks last-assigned user per (template, step_key) in `t_workflow_assignment_counter`. | B-1 | S72 |
| **D205** | Child workflow inherits parent field values via `input_mapping`; outputs mapped back via `output_mapping` (same pattern as Service step D186). | B-1 | S72 |

## Workflow Management Workbench

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D206** | Runtime workflow interaction is consolidated into a single workbench showing current step status, assignee, SLA, form, attachments, and full step timeline. | Workflow management gap analysis | S73 |
| **D207** | Human steps support controlled file attachments at step-instance level. Allowed types are business documents and evidence files on an allowlist; CAD, archives, executables, and arbitrary binaries are blocked. | Workflow management gap analysis | S73 |
| **D208** | Step assignment actions are explicit: assign, accept, delegate, override next assignee, reassign by admin/team lead, and escalate on SLA breach. Every change is audited in action history. | Workflow management gap analysis | S73 |
| **D209** | Workflow status is displayed at three levels: workflow instance status, current step status, and derived action display status. The workbench always shows all three together to avoid ambiguity. | Workflow management gap analysis | S73 |
| **D210** | Step forms save draft values independently of completion. Completion enforces required fields; read-only context fields and attachments remain visible to later steps according to template config. | Workflow management gap analysis | S73 |

## Taxonomy Consolidation

| ID | Decision | Source | R-File |
|----|----------|--------|--------|
| **D211** | User-facing taxonomy terminology is consolidated on **Category** for the strategic classification stored in `t_topic` / `TOP_*`; the term **Business Theme** is retired from active specs and UI copy. | 2026-03-17 taxonomy update | R00, R08 |
| **D212** | Category attachment cardinality is standardized to **max 2** for Actions, Meetings, and Meeting Decisions. Actions require at least 1 category; the others may have 0..2. Workflow instances do not store categories. | 2026-03-17 taxonomy update | R01, R08, R17, R16 |
| **D213** | Category filters, dashboard KPIs, summaries, and search results must match an entity when either attached category equals the selected category. Entities attached to 2 categories are counted in both category scopes. | 2026-03-17 taxonomy update | R05, R17 |
| **D214** | `Action Type` and per-category leader assignment are retired from the active product model, specs, and UI. Strategic classification is represented only by Category (`t_topic` / `TOP_*`). | 2026-03-17 taxonomy simplification | R00, R01, R05, R06, R08 |
