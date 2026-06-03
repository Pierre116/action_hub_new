# ActionHub — User Guide

This guide is for people using ActionHub in daily work: administrators, team leaders, contributors, and process owners.

For coding-agent instructions, use `AGENTS.md` instead of this file.

---

## 1. What ActionHub Covers

ActionHub has six core working areas:

- **Dashboard**: personal and category-oriented work visibility
- **Actions**: operational tasks with owners, participants, deadlines, and status tracking
- **Meetings**: meeting series, occurrences, attendance, and meeting-linked work
- **Decisions**: formal meeting outcomes that remain searchable and trackable
- **Workflow**: process requests and step-by-step execution for workflows such as approvals, ECO, or ID creation
- **Admin**: users, teams, and category configuration

---

## 2. Who Uses What

| User group | Main areas |
|------------|------------|
| Administrator | Admin, dashboard, actions, workflow builder, workflow dashboard |
| Team leader / manager | Dashboard, actions, meetings, decisions, workflow dashboard |
| Contributor | Personal dashboard, actions, meetings, decisions, workflow workbench |
| Process owner | Workflow dashboard, workflow builder, workflow runtime validation |

Notes:

- The current UI exposes the **workflow builder** from the top navigation only for **Admin** users.
- Some backend checks still recognize `TeamLead` for compatibility, but the main SPA navigation is admin-vs-authenticated-user in practice.

---

## 3. Login and Session Behavior

1. Open ActionHub in the browser.
2. Sign in with your username and password.
3. After login, the SPA stores your session with JWT access and refresh tokens for API calls.
4. Use the language toggle in the top-right area to switch between English and Chinese.
5. Use the user menu to log out.

If your session expires, ActionHub redirects you back to the login screen.

---

## 4. Main Navigation

After login, the top navigation provides:

- **Dashboard**
  - Personal Dashboard
  - Category Dashboard
- **Actions**
- **Meeting Series**
- **Decisions**
- **Instructions**
- **Workflow**
  - Workflow Dashboard
  - Workflow Builder (Admin only)
- **Admin** (Admin only)
  - Users
  - Teams
  - Categories

The **Instructions** page surfaces the in-app SOP for common flows.

---

## 5. Common Workflows

### 5.1 Personal Dashboard

Use the personal dashboard to review:

- actions assigned to you
- due and overdue work
- decision and workflow workload indicators where available
- progress summaries for current work

Current dashboard interpretation:

- the personal dashboard is the main daily-entry page for contributors and managers
- actions and workflow steps are related, but they should be treated as separate work object types
- workflow items should be opened in the workflow workbench when you need to execute the step itself

### 5.2 Actions

Use the action area to:

- create a new action
- open an existing action
- update its title, dates, categories, assignments, and status
- review comments, history, and linked workflow information when present

Current operating rules to remember:

- workflows are **not** auto-started when you create an action
- non-meeting actions are tightly controlled around the creator/owner model
- meeting-created actions follow meeting participant constraints

### 5.3 Meetings and Decisions

Use **Meeting Series** to manage recurring or structured meetings.

Typical flow:

1. Open a meeting series.
2. Open the target occurrence workspace.
3. Review or update participants and meeting details.
4. Add actions and decisions from the meeting context.
5. Use the occurrence workspace as the source of truth for follow-up items.

### 5.4 Workflow Dashboard and Runtime

Workflows in ActionHub follow a **process-first** model.

- Start and monitor workflows from the **Workflow** area.
- Treat workflow steps as process work, not as sub-actions.
- Use action-linked workflow behavior only when maintaining compatibility with older records.
- After launching a workflow request, continue work from the **workflow workbench**.

The workflow dashboard is the primary operational surface for:

- viewing available templates
- starting process workflows
- monitoring in-flight instances
- opening current workbench steps

Important current-state note:

- new request-type workflows run directly as workflow instances and do not require a supporting action record
- older action-linked workflow records still appear in some compatibility paths, but day-to-day process execution should happen in the workflow dashboard and workbench

### 5.5 Admin

Administrators manage:

- users
- teams
- categories
- workflow templates

Use the admin area when changing reference data that affects many users.

---

## 6. Instructions and SOPs

Use these documentation entry points:

- `HOW_TO.md`: this operational guide
- `/instructions`: in-app instructions screen
- `specs/specifications/S90_SOP_Main_User_Flows.md`: English SOP
- `specs/specifications/S90_SOP_Main_User_Flows.zh.md`: Chinese SOP

---

## 7. Known Operating Constraints

- Most data is broadly visible to authenticated users; treat the system as an internal operational tool, not a confidential record store.
- Private meeting/action visibility exists in limited areas, but ActionHub is not designed for sensitive or regulated data storage.
- Workflow templates and runtime are still evolving under the process-first model; follow the workflow dashboard as the primary runtime surface.

---

## 8. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Sent back to login | token expired or missing | sign in again |
| Workflow does not start from a new action | expected behavior | start it from the workflow area if needed |
| Workflow launch opens a workbench instead of action detail | expected behavior | continue the process from the workflow workbench; use the related action link only when you need action metadata |
| Cannot see admin menus | user is not Admin | ask an administrator to verify your role |
| Instructions page missing content | SOP markdown file mismatch | report it to the admin or maintainer |

---

## 9. Maintainer Notes

If this guide drifts from the live SPA, update it together with:

- `README.md`
- `CODE_GENERATION_PLAN.md`
- `specs/README.md`
- `specs/specifications/S80_react_frontend_architecture.md`
- `specs/specifications/S90_SOP_Main_User_Flows.md`
