# Validation Summary — 2026-03-19

## Scope

- Documentation reassessment for core user-facing and core-operational modules
- Roadmap reconciliation with as-built code
- Small code fixes discovered during audit
- Workflow runtime UX alignment with the process-first operating model
- Request-workflow runtime decoupling so standalone requests no longer require supporting action persistence

## Files Updated

- README.md
- HOW_TO.md
- CODE_GENERATION_PLAN.md
- specs/README.md
- specs/requirements/R06_security.md
- specs/requirements/R09_ui_content.md
- specs/requirements/R13_testing.md
- specs/requirements/R16_workflow_app_extension.md
- specs/specifications/S16_API_Contract.md
- specs/specifications/S70_workflow_engine_v3.md
- specs/specifications/S73_workflow_management_workbench.md
- specs/specifications/S74_meeting_action_topic_inheritance.md
- specs/specifications/S75_workflow_ui_react_flow_update.md
- specs/specifications/S80_react_frontend_architecture.md
- specs/specifications/S90_SOP_Main_User_Flows.md
- specs/specifications/S90_SOP_Main_User_Flows.zh.md
- action_hub/frontend/src/components/workflow/WorkbenchPanel.tsx
- action_hub/frontend/src/lib/i18n.ts
- action_hub/frontend/src/pages/dashboard/Personal.tsx
- action_hub/frontend/src/pages/workflow/Dashboard.tsx
- action_hub/frontend/src/pages/workflow/Workbench.tsx
- action_hub/frontend/src/router.tsx
- action_hub/actionhub/workflow/assignment.py
- action_hub/actionhub/workflow/approval_service.py
- action_hub/actionhub/workflow/dashboard_service.py
- action_hub/actionhub/workflow/engine.py
- action_hub/actionhub/workflow/routes.py
- action_hub/actionhub/workflow/service.py
- action_hub/tests/test_workflow_assignment.py

## Code Fixes

- Added the missing `/instructions` SPA route so the navigation link resolves correctly.
- Added a real SPA route and page for `/workflow/workbench/:instanceId`.
- Changed workflow request launch to open the workflow workbench instead of treating action detail as the primary runtime surface.
- Updated dashboard workflow links and payload handling to support standalone process requests and nullable action linkage.
- Removed the default supporting-action creation path from request-type workflow launch.
- Updated workflow engine logging and workflow queries so request instances can run with `wfi_action_id = NULL`.

## Validation

- Frontend changed-file diagnostics: no blocking editor errors reported on the edited SPA files.
- Frontend production build: passed.
- Full backend pytest: passed.

### Full Backend Pytest Result

- 312 passed
- 475 warnings
- Total runtime: 228.14s (0:03:48)

### WF-26 Validation Slice

- Focused workflow regressions: 17 passed, 49 warnings in 16.49s
- Full workflow backend slice: 79 passed, 122 warnings in 37.85s

### Warning Notes

- `InsecureKeyLengthWarning` remains for JWT HMAC keys below the recommended length.
- Python 3.12 emits sqlite datetime adapter deprecation warnings in the current stack.

These warnings were pre-existing follow-up items and were not expanded into a separate remediation batch during this reconciliation pass.

## Closeout

- User guidance, requirements, specifications, and roadmap are now aligned to the live SPA and current process-first workflow behavior.
- The workflow dashboard and workflow workbench are now the primary documented runtime surfaces for process workflows.
- Request-type workflows now run without mandatory supporting action persistence.
- Remaining future work stays tracked separately in the roadmap, notably `WF-25` and `P12`.