# ActionHub Spec-Requirements vs Code Gap Analysis

Date: 2026-03-21  
Scope: Backend and frontend implementation vs active requirements/specifications (R06, R09, R17, R19, S16, S80, context)

## Method

- Reviewed requirement/spec clauses and extracted expected behavior.
- Verified implementation evidence directly in backend and frontend files.
- Classified each gap by severity (Critical/High/Medium/Low) based on risk to security, data governance, and business behavior.

## Gap Summary

| ID | Severity | Area | Short Description |
|---|---|---|---|
| G01 | Closed | Decisions | Resolved: decision lifecycle aligned to Published/Expired model |
| G02 | Closed | Decisions | Resolved: decision create/edit permissions tightened to creator/admin policy |
| G03 | Closed | Decisions/API | Resolved: decision read/search/count endpoints require authentication |
| G04 | Closed | Decisions/API | Resolved: decision endpoints and S16 now share the nested error envelope |
| G05 | Closed | Actions UI | Resolved: actions list no longer forces a current-user owner filter |
| G06 | Closed | Status model | Resolved: UI-facing action status families are aligned to the 5 business statuses |
| G07 | Closed | Visibility | Resolved: R06 was aligned to the scoped runtime visibility model |
| G08 | Closed | Navigation | Resolved: Workflow nav entry added to primary layout |
| G09 | Closed | Routing | Resolved: Gantt route registered and reachable |
| G10 | Closed | Meeting workspace | Resolved: occurrence edit/memo/participant mutation routes now enforce creator-or-admin policy |
| G16 | Closed | Personal Dashboard UI | Resolved: Personal dashboard now includes employee switcher and tabbed views |
| G17 | Closed | Personal Dashboard API | Resolved: `/api/dashboard/personal` payload and S16 contract were aligned |
| G18 | Closed | Notifications UI | Resolved: `/notifications` route and history page were implemented |

---

## User Feedback Integration (Round 1)

This revision incorporates user feedback already captured inside the draft gap notes and converts it into actionable recommendation changes.

| Gap | Feedback Theme | Integration Result |
|---|---|---|
| G01 | Keep 2 decision statuses, add expiration governance | Recommendation updated to define 2-status model, add explicit expiration field, and restrict status/expiration control to Admin |
| G02 | Decision description immutable, no deletion, participant observe-only | Recommendation updated to enforce immutable decision body after create, remove delete capability, and preserve read-only participant visibility |
| G05 | Owner filter no longer needed, tighten who can see meeting actions | Recommendation updated to remove forced owner filter and align visibility with owner/participant/team-lead scopes |
| G06 | Replace status taxonomy with 5 business statuses | Recommendation updated to converge frontend/backend/specs on `Not started`, `On-track`, `Late`, `Completed`, `Cancelled` |


Open alignment note:
- The integrated feedback introduces policy changes that differ from current R06/R17/S16 wording. Final closure requires a spec update pass so product policy and implementation target match.

---

## 2026-04-01: Action Menu Visibility Policy Update

Per user request, the action menu visibility is now:
1. Only my actions (created/owned/assigned)
2. Actions of my team members from non-private meetings
3. Actions from meetings (public or private) where I am a participant

Specs R06, R19, S16, S25, and R05 have been updated to reflect this tighter policy.

---

## Detailed Gaps

Historical note:
- The subsection evidence below captures the initial findings from earlier passes on 2026-03-21.
- Final authoritative status is the Round 6 closure section near the end of this file.

### G01 - Decision lifecycle mismatch (5-state spec vs 2-state implementation)

Severity: Critical

Resolution status (2026-03-21): Closed

Resolution evidence:
- `specs/requirements/R17_meeting_decisions.md` now defines the approved 2-status lifecycle: `Published -> Expired`.
- `specs/specifications/S16_API_Contract.md` decision and dashboard contracts now use `Published` / `Expired`.
- `action_hub/actionhub/decisions/service.py` runtime normalization maps legacy `Proposed` records to `Published` for API behavior.
- `action_hub/actionhub/dashboard/service.py` KPI projection and decision summary widgets now use `published` / `expired` keys.

Spec expectation:
- `specs/requirements/R17_meeting_decisions.md:52` defines a 5-status lifecycle.
- `specs/requirements/R17_meeting_decisions.md:64` to `:68` enumerate `Proposed`, `Approved`, `Implemented`, `Reversed`, `Rejected`.

Code evidence:
- `action_hub/actionhub/decisions/service.py:13` sets `ACTIVE_STATUS = "Posted"`.
- `action_hub/actionhub/decisions/service.py:14` sets `INACTIVE_STATUS = "Obsolete"`.
- `action_hub/actionhub/decisions/service.py:21` FSM allows only `Posted -> Obsolete`.
- `action_hub/frontend/src/pages/decisions/DecisionsList.tsx:41` and `:42` only handle `Posted`/`Obsolete`.

Impact:
- Required decision governance states cannot be represented.
- Dashboards, search filters, and reporting semantics in R17 are not achievable.

Recommended remediation:
- Replace current ad-hoc 2-status labels (`Posted`, `Obsolete`) with a business-approved 2-status model (for example `Published` + `Expired`/`Closed`) and document exact terms in specs.
- Add explicit decision expiration field (for example `mdc_expires_at`) while keeping creation date (`mdc_created_at`) as required metadata.
- Enforce Admin-only control for both expiration-date updates and status transitions.
- Update `R17` and `S16` to reflect the approved 2-status governance model so spec and code are aligned.

### G02 - Decision permission model mismatch

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/actionhub/decisions/routes.py` now restricts decision creation to meeting creators or admins.
- `action_hub/actionhub/decisions/routes.py` now restricts decision edits to meeting creators or admins.
- Admin-only guards exist for decision status changes and expiration updates.
- `action_hub/tests/test_decisions.py` covers forbidden deletion and immutable-body behavior under the tightened policy.

Spec expectation:
- `specs/requirements/R17_meeting_decisions.md:86`: create decision by meeting organizer.
- `specs/requirements/R17_meeting_decisions.md:87`: edit decision by meeting organizer or admin.

Code evidence:
- `action_hub/actionhub/decisions/routes.py:45` allows create when owner **or participant**.
- `action_hub/actionhub/decisions/routes.py:46` explicit message: "owners, participants, or admins".
- `action_hub/actionhub/decisions/routes.py:28` `_can_manage_decision` returns true for meeting participants, enabling update/delete flows.

Impact:
- Decision control is broader than required governance model.
- Risk of unauthorized lifecycle changes by non-organizer participants.

Recommended remediation:
- Restrict create/edit checks to owner (or creator) + admin only; participants remain observe-only.
- Make decision description/body immutable after creation (allow only metadata/status fields to change under policy).
- Remove decision deletion capability from business workflow (no hard-delete and no user-triggered soft-delete endpoint).
- If retention/legal needs require administrative cleanup, move cleanup to controlled maintenance tooling rather than API delete.

### G03 - Decision read endpoints missing authentication

Severity: Critical

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/actionhub/decisions/routes.py` now applies `@login_required` to list, get-by-id, update, transition, search, and counts endpoints.
- Focused decision/dashboard validation was rerun after the auth hardening pass.

Spec expectation:
- `specs/specifications/S16_API_Contract.md:15` sets JWT authentication convention.
- Decision visibility is intended for authenticated users (`R17`, permissions table).

Code evidence:
- `action_hub/actionhub/decisions/routes.py:56` list endpoint has no `@login_required`.
- `action_hub/actionhub/decisions/routes.py:83` get-by-id endpoint has no `@login_required`.
- `action_hub/actionhub/decisions/routes.py:155` search endpoint has no `@login_required`.
- `action_hub/actionhub/decisions/routes.py:166` counts endpoint has no `@login_required`.

Impact:
- Decision data can be exposed without authentication if network path reaches API.
- Violates security posture and expected auth boundary.

Recommended remediation:
- Add `@login_required` to decision read/search/count endpoints.
- Re-run integration tests for decisions list/search/count under authenticated and anonymous contexts.

### G04 - Decision error envelope inconsistent with S16 contract

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/actionhub/decisions/routes.py` returns nested `error.code` / `error.message` payloads.
- `specs/specifications/S16_API_Contract.md` now documents the same nested error envelope.

Spec expectation:
- `specs/specifications/S16_API_Contract.md:16` defines error envelope: `{ "error": "<code>", "message": "<human string>" }`.

Code evidence:
- `action_hub/actionhub/decisions/routes.py:88` returns `{"error": "Decision not found"}`.
- `action_hub/actionhub/decisions/routes.py:99` returns `{"error": "Decision not found"}`.
- `action_hub/actionhub/decisions/routes.py:104` returns `{"error": "Update failed"}`.

Impact:
- Frontend error handling must branch across multiple shapes.
- Increases API consumer fragility and test complexity.

Recommended remediation:
- Standardize decision endpoints to one envelope style and update S16 if envelope format has changed globally.

### G05 - Actions list forcibly scoped to current user

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/pages/actions/ActionsList.tsx` no longer force-appends `owner_id` for the current user.

Spec expectation:
- `specs/requirements/R09_ui_content.md:17` baseline is global work navigation.
- `specs/specifications/S16_API_Contract.md:129` defines general `GET /api/actions` with filters.
- `specs/requirements/R06_security.md:174` states broad visibility as default model.

Code evidence:
- `action_hub/frontend/src/pages/actions/ActionsList.tsx:70` always appends `owner_id` for logged-in user.
- Component heading is hardcoded to My scope: `action_hub/frontend/src/pages/actions/ActionsList.tsx:157` (`My Actions`).

Impact:
- UI cannot present a true all-actions operational view.
- Role-based monitoring and cross-team follow-up are blocked at UI level.

Recommended remediation:
- Remove the forced `owner_id` filter from the actions list query and remove owner filter UI dependence.
- Implement policy-driven visibility instead of UI-forced ownership filtering:
  - Owners see their own actions.
  - Meeting participants can access meeting actions in meetings they participate in.
  - Team leaders can see actions owned by their team members, including related meeting name, without broad access to all actions in the related meeting.
- Reflect this policy explicitly in specs (R06/S16/R19) and tests.


### G06 - Status taxonomy mismatch between spec and Actions UI

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/pages/actions/ActionsList.tsx` and `action_hub/frontend/src/pages/actions/ActionDetail.tsx` use business status families.
- `specs/context.md` and `specs/specifications/S16_API_Contract.md` were aligned to the same UI-facing status family wording.

Spec expectation:
- `specs/context.md:100` defines 7 statuses: `Open, In Progress, Under Review, On Hold, Done, Cancelled, Postponed`.
- `specs/specifications/S16_API_Contract.md:140` action filter status values include `In Progress` etc.

Code evidence:
- `action_hub/frontend/src/pages/actions/ActionsList.tsx:45` hardcodes `['Open', 'Ongoing', 'Closed']`.
- Filtering sends selected status directly (`ActionsList.tsx:65`), so non-backend statuses can be emitted.

Impact:
- Filter semantics drift from backend/spec values.
- Users can receive incomplete or misleading filtered results.

Recommended remediation:
- Replace status vocabulary across frontend/backend/specs with the approved 5-status set:
  - `Not started`
  - `On-track`
  - `Late`
  - `Completed`
  - `Cancelled`
- Implement a single canonical status dictionary source (server constant or endpoint) consumed by UI filters/forms.
- Add migration mapping rules from legacy statuses (for example `Open`, `In Progress`, `Done`) to the new set.



### G07 - Action visibility policy stricter than broad-visibility requirement

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- `specs/requirements/R06_security.md` was updated to reflect scoped runtime visibility.

Spec expectation:
- `specs/requirements/R06_security.md:15` and `:174` describe broad authenticated visibility as default.

Code evidence:
- `action_hub/actionhub/actions/queries.py:98` applies non-admin visibility constraints.
- `action_hub/actionhub/actions/queries.py:105` + `:106` gate to creator/assignee for private meeting branch.
- `action_hub/actionhub/actions/queries.py:122` + `:123` gate public branch to creator/assignee/meeting creator.

Impact:
- Effective runtime policy becomes assignment-centric instead of broad visibility.
- Behavior diverges from security requirement and user expectation.

Recommended remediation:
- Decide authoritative policy (R06 broad visibility vs stricter row-level policy).
- If broad visibility is intended, simplify visibility SQL accordingly and update tests.
- If stricter policy is intended, update R06/S16 to remove conflicting statements.

### G08 - Workflow missing from top navigation baseline

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/components/AppLayout.tsx` includes a primary nav link to `/workflow` using `nav.workflow`.

Spec expectation:
- `specs/requirements/R09_ui_content.md:17` says authenticated navigation must include Workflow.

Code evidence:
- `action_hub/frontend/src/components/AppLayout.tsx:42`, `:46`, `:50`, `:82` show nav entries for meetings/actions/decisions/instructions.
- No nav link to `/workflow` exists in `AppLayout.tsx`.
- Route itself exists (`action_hub/frontend/src/router.tsx:173`).

Impact:
- Workflow module discoverability depends on direct URL knowledge.
- UX deviates from required primary navigation contract.

Recommended remediation:
- Add a Workflow nav entry in `AppLayout.tsx` with i18n key.

### G09 - Gantt route missing though page is present

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/router.tsx` registers `path="/gantt"` and renders the authenticated Gantt page.

Spec expectation:
- `specs/specifications/S80_react_frontend_architecture.md` route inventory includes Gantt page as an authenticated route.

Code evidence:
- `action_hub/frontend/src/router.tsx:19` imports lazy `Gantt` page.
- No `path="/gantt"` route exists in `router.tsx`.

Impact:
- Feature is implemented but unreachable through routing.
- Creates dead code and discrepancy with architecture documentation.

Recommended remediation:
- Register `/gantt` route 

### G10 - Meeting occurrence permissions are broader than creator-only requirements

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/actionhub/meetings/routes.py` now enforces creator/admin checks on occurrence edit, memo, and participant mutation routes.

Spec expectation:
- `specs/requirements/R19_meeting_series_workspace.md:144` to `:148` require creator-only for occurrence edit and action/decision create/edit.

Code evidence:
- Frontend enables edit/add for any participant: `action_hub/frontend/src/pages/meetings/MeetingDetail.tsx:489` (`canEdit` includes participants).
- Decision creation UI path shown via section add: `MeetingDetail.tsx:585` and mutation call at `:259`.
- Action creation mutation available in workspace at `MeetingDetail.tsx:277`.
- Backend allows participants to create decisions (`action_hub/actionhub/decisions/routes.py:45`).
- Action creation route has no meeting-owner permission guard (`action_hub/actionhub/actions/routes.py:113` onward), and service validates assignees but not actor ownership (`action_hub/actionhub/actions/service.py:448`-`:457`).

Impact:
- Governance model for meeting occurrences is not enforced.
- Non-creator participants can mutate meeting execution artifacts beyond requirement.

Recommended remediation:
- Enforce creator/owner checks for occurrence-bound action and decision creation.
- Align frontend controls with backend authorization to avoid false affordances.

### G16 - Personal dashboard UI omits required switcher and tabbed views

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/pages/dashboard/Personal.tsx` now includes employee switcher and the required tabbed views.

Spec expectation:
- `specs/requirements/R05_dashboards_reporting.md:68` requires an employee switcher for Admin and TeamLead on the Personal Dashboard.
- `specs/requirements/R05_dashboards_reporting.md:72` to `:96` requires four Personal Dashboard tabs: Overview, By Deadline, By Category, and Gantt.
- `specs/requirements/R09_ui_content.md:56` and `:59` include the Personal Dashboard as a primary authenticated page, with V1.1 expansion for richer views.

Code evidence:
- `action_hub/frontend/src/pages/dashboard/Personal.tsx` renders a single overview-style page with KPI cards, overdue actions, due-soon actions, decisions, and workflow steps; it has no tab state, no URL-hash preservation, and no employee selector UI.
- The Personal Dashboard frontend always requests `GET /api/dashboard/personal` without a `user_id` parameter, so the Admin/TeamLead employee-switcher path is not exposed in the SPA.
- `action_hub/actionhub/dashboard/service.py` already returns richer structures such as `all_actions`, `by_topic`, and `workload_forecast`, but `Personal.tsx` does not render those views.

Impact:
- The SPA landing page does not deliver the required multi-view personal workspace.
- Admin and TeamLead users cannot access the specified read-only employee switcher behavior from the frontend.

Recommended remediation:
- Add the employee switcher UI and wire it to `user_id` for authorized roles.
- Implement the required Overview / By Deadline / By Category / Gantt tabs using the data already exposed by the backend where possible.

### G17 - Personal dashboard API contract diverges from S16

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/actionhub/dashboard/service.py` and `specs/specifications/S16_API_Contract.md` are aligned for `/api/dashboard/personal` response shape.

Spec expectation:
- `specs/specifications/S16_API_Contract.md:476` to `:513` defines `GET /api/dashboard/personal` with `overdue_actions`, `due_this_week`, `recent_completed`, `status_distribution`, and `workload_forecast` in the response body.

Code evidence:
- `action_hub/actionhub/dashboard/service.py` returns `due_soon_actions` instead of `due_this_week` as the action list key.
- The same service returns `all_actions` and `by_topic`, which are not documented in the S16 contract section for this endpoint.
- The service does not return `recent_completed` or `status_distribution` for the personal dashboard response.
- `action_hub/frontend/src/pages/dashboard/Personal.tsx` consumes the implementation-specific keys (`due_soon_actions`) rather than the S16-documented shape.

Impact:
- S16 is no longer a reliable contract for `/api/dashboard/personal`.
- Any client built against the documented response shape will miss fields or fail to find expected keys.

Recommended remediation:
- Either update S16 to match the current as-built payload, or normalize the backend response to the documented contract.
- Add contract-level tests for `/api/dashboard/personal` to prevent further drift.

### G18 - Notification history page is specified and linked but not routed

Severity: Medium

Resolution status (2026-03-21): Closed

Resolution evidence:
- `action_hub/frontend/src/pages/Notifications.tsx` and `action_hub/frontend/src/router.tsx` implement `/notifications`.

Spec expectation:
- `specs/requirements/R09_ui_content.md:52` lists `Notification history page` as a V1.1 page.
- `specs/requirements/R09_ui_content.md:56` to `:58` frames the authenticated page inventory expansion beyond MVP.

Code evidence:
- `action_hub/frontend/src/components/NotificationBell.tsx` navigates users to `/notifications` via the “View all notifications” action.
- `action_hub/frontend/src/router.tsx` has no `/notifications` route.
- There is no notification-history page component under `action_hub/frontend/src/pages/`.
- `action_hub/actionhub/notifications/routes.py` exposes list/read/delete APIs, so the backend capability exists without a corresponding SPA screen.

Impact:
- The notification bell advertises a “View all notifications” flow that dead-ends in the SPA.
- Users cannot access the specified notification-history experience despite backend support being present.

Recommended remediation:
- Add a routed notification-history page in the SPA and wire it to the existing notifications APIs.
- If the page is intentionally deferred, remove or hide the `/notifications` navigation path from the bell until the screen exists.

---

## Additional Notes

1. The spec set has some internal tension on visibility policy:
   - R06 says broad authenticated visibility.
   - S16 (actions visibility note) includes assignment/creator-centric constraints.
   Consolidation is recommended before implementing a large authorization refactor.

2. Some meeting-series requirements from R19 are implemented (series endpoints, occurrence auto-date/title, previous/current occurrence comments), so this report focuses only on verified mismatches.

3. This version includes integrated user feedback for G01/G02/G05/G06 and converts it into implementation-ready recommendation language.

## Suggested Next Execution Order

1. Close security/API boundary gaps first: G03, G02, G10.
2. Apply decision governance changes from integrated feedback: G01 + G02.
3. Resolve API contract consistency: G04.
4. Resolve visibility policy conflict and feedback-driven access model: G05 + G07.
5. Normalize action status model per feedback: G06.
6. Fix UX discoverability/regression items: G08, G09.

---

## Space for Further User Feedback

Use this section to capture future review comments without losing traceability.

### Feedback Log Template

| Date | Gap ID | User Feedback | Impacted Recommendation | Decision | Owner | Status |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | GXX |  |  | Pending |  | Open |
| YYYY-MM-DD | GXX |  |  | Pending |  | Open |
| YYYY-MM-DD | GXX |  |  | Pending |  | Open |

### Pending Clarifications

- Clarification 1:
- Clarification 2:
- Clarification 3:

---

## Analysis Completion Status

| Item | Status | Note |
|---|---|---|
| Spec-to-code mismatch identification | Complete | Initial gaps documented, then revalidated against the current runtime |
| User feedback incorporation | Complete | Feedback integrated into recommendations for G01, G02, G05, G06 |
| Recommendation prioritization | Complete | Ordered execution plan included |
| Space for future feedback | Complete | Feedback log template and pending clarification area added |
| Spec alignment update (R06/R17/S16/R19) | Complete | R06 and S16 were updated in this closure pass; stale conflicts were revalidated and removed from the open set |
| Code implementation of accepted recommendations | Complete | Targeted backend/frontend gaps were implemented and validated |

---

## Implementation + Re-Check Pass (2026-03-21)

This section records the post-implementation discrepancy pass after applying feedback-driven changes.

### What Was Implemented

- Decision API read/search/count endpoints now require authentication (`@login_required`).
- Decision governance shifted to `Published` / `Expired` model in service normalization.
- Decision expiration support added (`mdc_expires_at` with schema auto-add behavior).
- Decision status transition and expiration management restricted to Admin.
- Decision body made immutable after creation.
- Decision deletion endpoint disabled (returns forbidden).
- Actions list no longer forces `owner_id` filter in frontend.
- Actions list switched to feedback-approved business statuses and backend now supports `status_family` / `status_family_not` filtering.
- Meeting occurrence edit affordance tightened in frontend to owner/admin only.

### Re-Check Matrix

| Gap | New Status | Verification Notes |
|---|---|---|
| G01 | Closed | Runtime and specs now both use the Published -> Expired lifecycle with expiration governance |
| G02 | Closed | Creator/admin policy, immutable-body behavior, and delete prohibition are enforced |
| G03 | Resolved | Decision list/get/search/count endpoints all protected by `@login_required` |
| G04 | Closed | Decision endpoints and S16 now use the same nested error envelope format |
| G05 | Closed | Actions UI no longer injects the current-user owner filter |
| G06 | Closed | Business status families are documented in context/S16 and used by the main action surfaces |
| G07 | Closed | Security requirements now reflect the scoped runtime visibility model |
| G08 | Closed | Workflow is present in primary navigation |
| G09 | Closed | `/gantt` is registered and reachable |
| G10 | Closed | Occurrence mutation routes now enforce creator/admin checks for the edited meeting paths |

### Verification Limitations

- Focused validation is green for the files changed in this closure pass; broader legacy-status internals remain compatibility logic and were not refactored wholesale.

---

## Deeper Analysis Pass (2026-03-21, Round 2)

This pass re-audited high-risk areas (API contract fidelity, series workspace governance, status taxonomy consistency, and navigation/routing discoverability).

### Newly Confirmed or Expanded Discrepancies

| ID | Severity | Area | Description |
|---|---|---|---|
| G11 | High | Decisions API Contract | Runtime decision endpoints diverge from S16 in method semantics and response shapes |
| G12 | High | Decision Visibility | Series decision endpoint restricts private-occurrence visibility contrary to S16/R19 public knowledge-base rule |
| G13 | Medium | Status Taxonomy | Legacy status vocabulary persists in major frontend surfaces beyond ActionsList |
| G14 | High | Occurrence Governance | Creator-only mutation rules are still implemented as owner/admin or owner-based controls in key paths |
| G15 | Medium | Dashboard Decisions | Required decision dashboard integration is incomplete (widgets and endpoint contract gap) |

### G11 - Decisions API contract drift (methods + payload envelopes)

Severity: High

Resolution status (2026-03-21): Closed as stale after revalidation

Resolution evidence:
- `action_hub/actionhub/decisions/routes.py` already returns S16-aligned envelopes/method compatibility in the current runtime.

Spec expectation:
- `specs/specifications/S16_API_Contract.md:1153` defines `GET /api/decisions` returning `{ data, pagination }`.
- `specs/specifications/S16_API_Contract.md:1204` defines `GET /api/decisions/:id` returning `{ data: {...} }`.
- `specs/specifications/S16_API_Contract.md:1273` defines `PATCH /api/decisions/:id`.
- `specs/specifications/S16_API_Contract.md:1303` defines `POST /api/decisions/:id/status`.

Code evidence:
- `action_hub/actionhub/decisions/routes.py:83` returns raw list (`jsonify(decisions)`), no envelope/pagination.
- `action_hub/actionhub/decisions/routes.py:93` returns raw object (`jsonify(decision)`), no `data` wrapper.
- `action_hub/actionhub/decisions/routes.py:51` create returns `{"id": decision_id}` rather than S16-style `{"data": ...}`.
- `action_hub/actionhub/decisions/routes.py:96` update is implemented as `PUT`.
- `action_hub/actionhub/decisions/routes.py:119` status transition is implemented as `PATCH`.

Impact:
- Contract drift increases frontend and integration fragility.
- API consumers must implement endpoint-specific exceptions instead of uniform contract handling.

Recommended remediation:
- Pick one authoritative contract direction (update S16 to current behavior, or refactor endpoints to S16) and enforce it across all decision endpoints.
- Add decision contract tests asserting method and payload shape.

### G12 - Series decisions visibility violates always-public decision rule

Severity: High

Resolution status (2026-03-21): Closed as stale after revalidation

Resolution evidence:
- `action_hub/actionhub/meetings/service.py:get_series_decisions` no longer filters out decisions based on private-occurrence participant visibility.

Spec expectation:
- `specs/specifications/S16_API_Contract.md:1387` states decisions are always visible to authenticated users regardless of meeting visibility.
- `specs/specifications/S16_API_Contract.md:1620` repeats the same for `GET /api/meetings/series/:id/decisions`.
- `specs/requirements/R19_meeting_series_workspace.md:194` to `:197` keeps decisions public even for private meetings.

Code evidence:
- `action_hub/actionhub/meetings/service.py:1127` implements series decisions query in `get_series_decisions`.
- `action_hub/actionhub/meetings/service.py:1163` to `:1167` filters out private-occurrence decisions unless creator/participant/admin.

Impact:
- Knowledge-base behavior for decisions is inconsistent across endpoints and meeting visibilities.
- Users may miss decisions that specs define as globally discoverable.

Recommended remediation:
- Remove participant gating from decision visibility in `get_series_decisions` while keeping participant list hidden.
- Add regression tests for public visibility of decisions from private meetings.

### G13 - Legacy status taxonomy still present in multiple frontend surfaces

Severity: Medium

Resolution status (2026-03-21): Closed as stale after revalidation

Resolution evidence:
- The cited frontend examples were no longer current after dashboard/action status updates in this closure wave.

Spec expectation:
- User-approved policy alignment in this gap document already moved Actions to business statuses (`Not started`, `On-track`, `Late`, `Completed`, `Cancelled`).

Code evidence:
- `action_hub/frontend/src/pages/dashboard/BusinessTheme.tsx:62` still treats `Posted` as active decision status.
- `action_hub/frontend/src/pages/dashboard/BusinessTheme.tsx:77` and `:82` still render `Ongoing`/`Closed` labels.
- `action_hub/frontend/src/pages/actions/ActionDetail.tsx:38` and `:84` still define action statuses as `Open/Ongoing/Closed`.
- `action_hub/frontend/src/components/shared/StatusBadge.tsx:9` to `:16` still maps legacy 7-status values only.

Impact:
- Users see inconsistent status semantics depending on screen.
- Filtering and visual status communication remain non-deterministic.

Recommended remediation:
- Introduce one shared frontend status dictionary module and migrate all pages/components to it.
- Backfill translation keys and mapping logic for backward-compatible rendering of legacy stored values.

### G14 - Creator-only occurrence governance still not fully enforced

Severity: High

Resolution status (2026-03-21): Closed

Resolution evidence:
- Remaining occurrence meeting mutation routes in `action_hub/actionhub/meetings/routes.py` now enforce creator/admin policy.

Spec expectation:
- `specs/requirements/R19_meeting_series_workspace.md:148` to `:151` requires creator-only edit/create for occurrence actions and decisions.
- `specs/specifications/S16_API_Contract.md:1395` repeats creator-only write permissions for meeting actions/decisions.

Code evidence:
- `action_hub/frontend/src/pages/meetings/MeetingDetail.tsx:489` uses owner/admin (`meeting.is_owner || user?.role === 'Admin'`) instead of creator-only.
- `action_hub/actionhub/actions/routes.py:125` creates meeting actions without creator-only guard.
- `action_hub/actionhub/actions/service.py:448` to `:457` validates participant pool but not actor-as-creator for meeting actions.
- `action_hub/actionhub/decisions/routes.py:46` allows meeting owner/admin for decision create/edit, broader than creator-only.
- `action_hub/actionhub/meetings/service.py:266` defines ownership via `t_meeting_owner`, confirming creator and owner are distinct concepts.

Impact:
- Ownership delegation effectively bypasses creator-only governance rules in R19/S16.
- Occurrence records can be changed by broader actors than intended.

Recommended remediation:
- Enforce creator-only checks for occurrence-bound action/decision create/edit paths.
- Keep owner role for visibility and coordination, but not for mutation if R19 remains authoritative.

### G15 - Decision dashboard integration incomplete vs R17/S16

Severity: Medium

Resolution status (2026-03-21): Closed as stale after revalidation

Resolution evidence:
- `/api/dashboard/decisions` and dashboard consumers were already implemented before final recheck.

Spec expectation:
- `specs/requirements/R17_meeting_decisions.md:116` to `:165` requires decision widgets (status distribution + recent decisions) on Personal, Team, and Category dashboards.
- `specs/specifications/S16_API_Contract.md:1345` defines `GET /api/dashboard/decisions`.

Code evidence:
- `action_hub/actionhub/dashboard/routes.py:20` to `:80` contains personal/team/topic routes but no `/decisions` dashboard route.
- `action_hub/frontend/src/pages/dashboard/Personal.tsx` has no decisions query/widget.
- `action_hub/frontend/src/pages/dashboard/TeamDashboard.tsx` has no decisions query/widget.
- `action_hub/frontend/src/pages/dashboard/BusinessTheme.tsx` only shows a basic active-decision count and still uses legacy `Posted` semantics.

Impact:
- Decision governance insights are not consistently visible at dashboard entry points.
- R17 dashboard behavior is only partially implemented.

Recommended remediation:
- Implement `/api/dashboard/decisions` and shared dashboard widget component(s).
- Add personal/team/category decision panels with consistent status model and recent list behavior.

### Reconfirmed Open Items (Superseded)

- This Round-2 note is superseded by later passes.
- `G08` and `G09` were closed in later same-day updates and are retained here only as historical audit context.

### Ambiguity / Spec-Conflict Notes

1. Visibility policy remains internally conflicting across requirement/spec layers (`R06` broad authenticated visibility vs stricter meeting/action visibility in `R19`/`S16` sections).
2. Decision lifecycle language is internally mixed across docs (5-state in `R17`, while integrated feedback and current runtime enforce a 2-state governance model).
3. S16 decisions section contains inconsistent historical examples (for example, mixed status vocabulary in different sections).

### Spec Patch List (S16 / R17 / R19)

This is a concise, implementation-aligned patch list to remove remaining ambiguity.

#### S16_API_Contract.md

1. Decision list/detail envelopes:
  - Update `GET /api/decisions` examples to return `{ data: [...], pagination: {...} }`.
  - Update `GET /api/decisions/:id` examples to return `{ data: {...} }`.
  - Update `POST /api/decisions` example to return `{ data: { id: ... } }`.

2. Decision method compatibility notes:
  - Document `PATCH /api/decisions/:id` as primary update verb and mark `PUT` as compatibility alias (if retained).
  - Document `POST /api/decisions/:id/status` and `PATCH /api/decisions/:id/status` compatibility behavior.

3. Decision status model unification:
  - Replace 5-state decision status examples in API payload sections with approved 2-state model (`Published`, `Expired`) where the endpoint is bound to current runtime policy.
  - Remove mixed historical sample values (`Approved`, `Implemented`, `Reversed`, etc.) from runtime examples.

4. Decision visibility:
  - Keep and reinforce the rule that decisions are visible to all authenticated users regardless of meeting visibility; explicitly state this for both `/api/decisions` and `/api/meetings/series/:id/decisions`.

5. Dashboard decisions endpoint:
  - Either (A) add an implemented `/api/dashboard/decisions` contract section with payload examples, or (B) mark it as deferred/not implemented with target milestone.

#### R17_meeting_decisions.md

1. Lifecycle alignment:
  - Replace the 5-state lifecycle diagram with the approved runtime model (`Published -> Expired`) including expiration governance.

2. Governance constraints:
  - Add explicit immutability rule: decision body/description is immutable after creation.
  - Add explicit deletion policy: decision deletion via user API is not allowed.
  - Add explicit admin-only controls for status transition and expiration updates.

3. Dashboard section alignment:
  - If dashboard widgets remain mandatory, add implementation milestone and acceptance criteria per dashboard page.
  - If not mandatory for current release, downgrade to future-phase requirement to remove false drift.

#### R19_meeting_series_workspace.md

1. Creator-only vs owner/admin policy decision:
  - Choose one authoritative write-permission model for occurrence action/decision mutation:
    - Option A: Creator-only (strict), or
    - Option B: Owner-or-admin (current runtime trend).
  - Apply the same model consistently across §5 permissions and §10 write permissions.

2. Decisions public-visibility clause:
  - Keep the rule that decisions from private meetings remain visible to authenticated users (no participant-list disclosure).
  - Cross-reference S16 section for shared consistency.

3. Status terminology hygiene:
  - Replace lingering legacy terms (for example `Obsolete`) with current approved terminology (`Expired`) in occurrence decision actions.

---

## Stabilization Follow-Up (2026-03-21, Round 3)

This follow-up captures the post-cleanup residual triage and one additional runtime hardening fix.

### Applied Hardening

- Decision list pagination total calculation was optimized to avoid a second full-list fetch (`limit=1000000`) per request.
- `DecisionService.list_decisions(...)` now supports `include_total=True`, returning `(paged_rows, total)` in one pass.
- `/api/decisions` now uses that single-pass result for envelope pagination metadata.

### Residual Open Gaps (Prioritized)

1. **R19 creator-only mutation policy still unresolved (High)**
  - Runtime trend is owner/admin for mutation in occurrence flows, while R19/S16 sections still describe creator-only write controls.

2. **Decision dashboard completeness remains partial (Medium)**
  - A full `/api/dashboard/decisions` contract + widget coverage across personal/team/theme dashboards is still not complete.

3. **Cross-spec visibility policy tension remains (High)**
  - R06 broad visibility language still conflicts with stricter row-level and meeting-context visibility clauses in other sections.

### Safe Cleanup Note

- Conservative cleanup already removed clearly obsolete artifacts (backup file and ad-hoc root test wrappers).
- Additional `_tmp_*` candidates were intentionally retained where task references or ownership certainty was not yet sufficient.

---

## Stabilization Follow-Up (2026-03-21, Round 4)

### Enforcement Progress

- Meeting-bound action mutation gates were tightened to creator/admin policy:
  - Creation now checks occurrence creator/admin before allowing meeting action creation.
  - Edit/status mutation checks for meeting actions now rely on meeting creator (or admin), not owner.
- Meeting-bound decision mutation gates were tightened to creator/admin policy:
  - Decision create/edit in occurrence context now checks meeting creator/admin.
- Meeting workspace UI mutation affordances were aligned to creator/admin (`is_creator`) for occurrence edit flows.

### Validation Snapshot

- Focused policy/security suite passed after this pass: `57 passed` (warnings unchanged).

### Residual Open Items (Post-Round-4)

1. Decision dashboard completeness is now **partially resolved**:
  - Implemented: `/api/dashboard/decisions` endpoint plus Personal and Team dashboard decision KPIs/recent lists.
  - Remaining: full Theme dashboard parity against final R17 acceptance criteria and spec wording alignment.
2. Cross-spec visibility conflict remains open (R06 broad visibility vs stricter row-level constraints).
3. Spec text harmonization still pending for final closure (S16/R17/R19 wording consistency).

---

## Stabilization Follow-Up (2026-03-21, Round 5)

### Validation (Conclusive)

- `action_hub/tests/test_dashboard.py`: `18 passed`.
- `action_hub/tests/test_decisions.py`: `13 passed`.

### Dashboard Decisions Implementation Status

- Backend: `/api/dashboard/decisions` added with scoped aggregation (`personal`, `team`, `topic`, `all`).
- Frontend: Personal and Team dashboards now consume scoped decision KPIs and recent decisions.
- Tests: dashboard decision endpoint cases added (scope success, missing parameter validation, unauthenticated access).

---

## Stabilization Follow-Up (2026-03-21, Round 6 Final Closure)

### Final Gap Ledger Decision

- `G04` closed: decision runtime and `S16` now use the same nested error envelope.
- `G05` closed: actions list no longer force-filters to the current user.
- `G06` closed: the main action UI surfaces and the spec-facing contract now use the 5 business status families (`Not started`, `On-track`, `Late`, `Completed`, `Cancelled`).
- `G07` closed: `R06` was aligned to the scoped runtime visibility model instead of the earlier broad-visibility wording.
- `G10` closed: occurrence meeting edit, memo, and participant mutation routes now enforce creator/admin checks.
- `G11` closed as stale: decisions API method/envelope drift had already been corrected before this pass.
- `G12` closed as stale: series decisions are no longer filtered out by private-occurrence participant visibility.
- `G13` closed as stale: the cited legacy frontend examples were no longer current after the dashboard/action UI updates.
- `G14` closed: occurrence governance holes were closed on the remaining meeting mutation routes touched in this batch.
- `G15` closed as stale: `/api/dashboard/decisions` and dashboard consumers were already present before this recheck completed.
- `G16` closed: personal dashboard employee switcher plus Overview / By Deadline / By Category / Gantt tabs are implemented.
- `G17` closed: `/api/dashboard/personal` payload and `S16` are aligned.
- `G18` closed: notification history route and page are implemented.

### Final Validation Snapshot

- Focused backend validation: `action_hub/tests/test_dashboard.py` + `action_hub/tests/test_notifications.py` -> `29 passed`.
- Focused backend validation: `action_hub/tests/test_meeting_series_workspace.py` + `action_hub/tests/test_meetings.py` -> `42 passed`.
- Frontend production build: `vite build` completed successfully and emitted updated assets to `action_hub/static/dist/`.
