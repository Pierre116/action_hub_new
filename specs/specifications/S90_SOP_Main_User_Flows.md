
# S90 — Main User Flows SOP

**Date:** 2026-03-19  
**Version:** 2.0  
**Status:** ✅ Current  
**Depends On:** S16, S80, HOW_TO.md

---

## 1. Purpose

This SOP describes the main operational flows for the current ActionHub product:

- reviewing daily work
- creating and maintaining actions
- working from meetings and decisions
- using the workflow area for process workflows
- using admin screens for core reference data

---

## 2. Daily Start for Most Users

1. Sign in.
2. Open the **Personal Dashboard**.
3. Review overdue work, current actions, and any workflow items assigned to you.
4. Use the top navigation to jump to Actions, Meeting Series, Decisions, or Workflow as needed.

---

## 3. Creating or Updating an Action

### Typical path

1. Open **Actions**.
2. Create a new action or open an existing one.
3. Enter or update title, deadline, priority, and category information.
4. Save the record.
5. Review assignments, comments, and history.

### Important operating rules

- Actions do **not** automatically start workflows.
- Meeting-linked actions follow meeting participant restrictions.
- Private visibility behavior exists only in selected areas and should not be treated as full confidential-data support.

---

## 4. Working from Meetings

### Meeting series and occurrence flow

1. Open **Meeting Series**.
2. Select the target series.
3. Open the occurrence workspace.
4. Review participants, details, and follow-up items.
5. Create actions and decisions from the meeting context when needed.

### Rules to remember

- Meeting follow-up work should stay tied to the occurrence/workspace context when appropriate.
- Decisions are tracked separately from actions.

---

## 5. Creating and Reviewing Decisions

1. Open **Decisions** or create a decision from a meeting context.
2. Enter the decision title and key details.
3. Save the decision.
4. Use the decisions list to search, filter, and review outcomes later.

---

## 6. Workflow Operations

### Runtime model

ActionHub workflows are **process workflows**.

- Start from the **Workflow** area.
- Use workflow dashboards and workbench views to progress steps.
- Treat action-linked workflow display as a compatibility pattern, not the primary operating model.
- The current implementation may create a supporting action record for a workflow request, but users should continue the process from the workflow workbench.

### Process-owner flow

1. Open **Workflow Dashboard**.
2. Review templates or running instances.
3. Start or inspect a process workflow.
4. Open the current workbench step.
5. Accept, complete, reject, escalate, delegate, or attach supporting files as allowed.

### Builder flow

1. Open **Workflow Builder** (Admin-only in the current SPA navigation).
2. Load an existing template or start a new one.
3. Build and connect workflow steps.
4. Validate the graph.
5. Save the template.

## 7. Administrator Flow

Administrators maintain core platform setup:

1. Open **Admin**.
2. Review **Users**, **Teams**, and **Categories**.
3. Apply the required reference-data changes.
4. If workflows are in scope, maintain templates from the workflow builder.

---

## 8. Documentation Entry Points

- `README.md`: project and module overview
- `HOW_TO.md`: practical user guide
- `/instructions`: in-app documentation surface
- this SOP: stable day-to-day flow reference

---

## 9. Common Mistakes to Avoid

- expecting a workflow to auto-start from a newly created action
- treating workflow steps as action children in the same business model
- assuming every user can access admin or builder screens
- storing sensitive or regulated information in the app
