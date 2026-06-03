# R20 — Access Control Governance Addendum

> Status: Current
> Last updated: 2026-03-23
> Scope: Personal dashboard visibility, TeamLead scoped team view, meeting/occurrence content governance

---

## 1. Purpose

This addendum records the enforced runtime authorization policy for personal dashboard access and meeting-related governance rules.

---

## 2. Personal Dashboard Policy

1. The personal dashboard is self-scoped only.
2. Query parameter switching to another user is not allowed for TeamLead or Admin in the personal view.
3. Personal action panels include only actions created by the logged-in user.
4. Personal dashboard decision widget may display organization-wide decisions (scope: all), independent of personal action Lead scope.

---

## 3. TeamLead Dashboard Policy

1. TeamLead uses a dedicated team-scoped dashboard view.
2. TeamLead cannot use the personal dashboard to browse another user's personal data.
3. TeamLead dashboard lists only team-scope actions, including meeting-bound actions.
4. Team-scope actions are restricted to actions created by team members when no explicit Lead exists, or actions whose Lead assignee belongs to the led team.
5. Actions where the led team appears only as non-Lead assignees must not appear in team overdue/all-action lists.
6. For private-meeting actions where TeamLead is not permitted to view details, the row must be masked.
7. Masked rows expose only minimum operational metadata:
   - action status
   - meeting series ID
   - generic private-action marker text

---

## 4. Action Lead and Meeting-Bound Action Rules

1. Non-meeting action model remains creator-as-Lead (`act_created_by` = source user, `act_owner_id` = accountable Lead).
2. Meeting-bound actions are governed by meeting creator authority.
3. Meeting-bound action assignment is restricted to valid meeting participant scope.
4. A user can view actions assigned to them and actions from meetings where they are a participant, subject to private-content masking rules.

---

## 5. Meeting Participant Governance

1. Meeting-series occurrences inherit participant baseline from the parent series.
2. Occurrence participant updates are constrained to that series participant set.
3. Meeting creator must always remain a participant and cannot be removed.
4. Occurrence creator is auto-included as participant at creation time.

---

## 6. Meeting Content Visibility and Mutation Rights

1. Meeting content is viewable only by meeting owners and occurrence participants.
2. Public meeting metadata may be discoverable in list/search surfaces, but meeting content endpoints are still owner-or-participant only.
3. Meeting content mutation (including memo and participant management in occurrence workspace) is creator-or-admin only.
4. Routes returning meeting content must enforce visibility checks before returning payloads.
5. Meeting detail endpoint must return explicit `FORBIDDEN` when the meeting exists but caller is not an owner/participant; UI must render a dedicated no-access message for this case.
6. Meeting series detail endpoint is participant-gated regardless of `public/private` series flag: only Admin, series creator, default series participants, or users participating in at least one occurrence can open series detail.
7. Meeting series list may display lock-marked rows for inaccessible series and must show the owner name so users know whom to contact for participant access.

---

## 7. Governing Relationship

This addendum refines and operationalizes policy details across:

- R05 dashboards and reporting
- R06 security
- R19 meeting series workspace
- S16 API contract

Where wording conflicts exist, this addendum takes precedence for the covered scope until upstream sections are fully merged.