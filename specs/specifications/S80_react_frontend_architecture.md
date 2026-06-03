# S80 — React Frontend Architecture (As-Built)

> **Level**: L4 — Physical  
> **Date**: 2026-03-14  
> **Status**: As-built reference — documents the current React SPA architecture  
> **Source**: SEP-2 through SEP-4 implementation, `action_hub/frontend/`  
> **Depends on**: S60_frontend_backend_separation.md (migration plan)

---

## 1. Overview

ActionHub's frontend is a **React 18 Single Page Application** built with TypeScript and Vite 5. It replaces the Jinja2 + HTMX server-rendered frontend that was retired in SEP-4.

The SPA is served by Flask from `action_hub/static/dist/` (same-origin deployment). All data flows through JSON APIs (`/api/*`). Authentication uses JWT tokens (access + refresh).

---

## 2. Technology Stack

| Layer | Library | Version | Purpose |
|-------|---------|---------|---------|
| Framework | React | 18.2 | Component model, state, lifecycle |
| Language | TypeScript | 5.2 | Type safety, build-time contract checks |
| Build | Vite | 5.0 | Dev server + production bundler |
| Routing | React Router | 6.20 | Client-side URL routing, nested layouts |
| UI | react-bootstrap | 2.9 | Bootstrap 5 components in React |
| Data fetching | TanStack Query | 5.0 | Server-state cache, refetch, optimistic updates |
| Tables | TanStack Table | 8.0 | Headless sort, filter, pagination |
| Charts | react-chartjs-2 | 5.2 | Chart.js wrapper for dashboard KPIs |
| Forms | React Hook Form | 7.48 | Validation, dependent fields |
| HTTP client | Axios | 1.6 | API requests, interceptors for auth |
| Workflow canvas | @xyflow/react (React Flow) | 12.x | Node/edge graph editor for workflow builder |

### Not Used (by design)

| Library | Reason |
|---------|--------|
| `react-i18next` | Replaced with a lightweight custom `useTranslation()` hook (~340 lines) to avoid dependency; loads same `en.json`/`zh.json` catalogs |
| Redux / Zustand | TanStack Query handles server state; React Context sufficient for auth |
| CSS Modules / Tailwind | Bootstrap 5 via react-bootstrap covers all styling needs |
| Drawflow | Replaced by `@xyflow/react` (React Flow) in WF-24 for the workflow builder canvas |

---

## 3. Project Structure

```
action_hub/frontend/
├── index.html              ← Vite entry point
├── package.json            ← Dependencies and scripts
├── tsconfig.json           ← TypeScript config
├── tsconfig.node.json      ← TS config for Vite/Node
├── vite.config.ts          ← Vite build config
└── src/
    ├── main.tsx            ← React DOM mount, providers
    ├── App.tsx             ← Root component (delegates to router)
    ├── router.tsx          ← All route definitions, lazy loading
    ├── contexts/
    │   └── AuthContext.tsx  ← Auth state, login/logout, token management
    ├── lib/
    │   ├── api.ts          ← Axios instance with JWT interceptors
    │   ├── i18n.ts         ← Custom i18n (useTranslation hook, en/zh catalogs)
    │   └── i18n.d.ts       ← Type declarations for i18n
    ├── components/
    │   ├── AppLayout.tsx   ← Authenticated layout (navbar + main content)
    │   └── shared/
    │       ├── ChartPanel.tsx   ← Reusable chart wrapper
    │       ├── ConfirmModal.tsx ← Confirmation dialog
    │       ├── CrudTable.tsx    ← Generic CRUD table (TanStack Table)
    │       ├── DateField.tsx    ← Date input with formatting
    │       ├── KpiCard.tsx      ← Dashboard KPI card
    │       └── StatusBadge.tsx  ← Color-coded status badge
    └── pages/
        ├── Login.tsx
        ├── ChangePassword.tsx
        ├── Feedback.tsx
        ├── Gantt.tsx
        ├── Instructions.tsx
        ├── actions/
        │   ├── ActionsList.tsx
        │   └── ActionDetail.tsx
        ├── admin/
        │   ├── Users.tsx
        │   ├── Teams.tsx
        │   ├── ActionTypes.tsx
        │   ├── BusinessThemes.tsx
        ├── dashboard/
        │   ├── Personal.tsx
        │   ├── TeamDashboard.tsx
        │   └── BusinessTheme.tsx
        ├── meetings/
        │   ├── SeriesList.tsx
        │   ├── SeriesDetail.tsx
        │   └── OccurrenceWorkspace.tsx
        ├── decisions/
        │   └── DecisionsList.tsx
        ├── Notifications.tsx
        └── workflow/
            ├── Dashboard.tsx
          └── WorkflowBuilder.tsx
```

---

## 4. Routing Architecture

All routes are defined in `src/router.tsx` using React Router v6.

### Route Structure

| Path | Component | Auth Required | Lazy Loaded |
|------|-----------|:---:|:---:|
| `/login` | `Login` | No | Yes |
| `/` | Redirects to `/dashboard/personal` | Yes | — |
| `/dashboard/personal` | `DashboardPersonal` | Yes | Yes |
| `/dashboard/team` | `TeamDashboard` | Yes | Yes |
| `/dashboard/business-theme` | `DashboardBusinessTheme` | Yes | Yes |
| `/dashboard/category` | `DashboardBusinessTheme` | Yes | Yes |
| `/actions` | `ActionsList` | Yes | Yes |
| `/actions/:id` | `ActionsDetail` | Yes | Yes |
| `/meetings` | redirect to `/meetings/series` | Yes | — |
| `/meetings/series` | `SeriesList` | Yes | Yes |
| `/meetings/series/:id` | `SeriesDetail` | Yes | Yes |
| `/meetings/:id` | `OccurrenceWorkspace` | Yes | Yes |
| `/decisions` | `DecisionsList` | Yes | Yes |
| `/decisions/:id` | `DecisionDetail` | Yes | Yes |
| `/instructions` | `Instructions` | Yes | Yes |
| `/gantt` | `Gantt` | Yes | Yes |
| `/feedback` | `Feedback` | Yes | Yes |
| `/notifications` | `NotificationsPage` | Yes | Yes |
| `/change-password` | `ChangePassword` | Yes | Yes |
| `/admin/users` | `AdminUsers` | Yes | Yes |
| `/admin/teams` | `AdminTeams` | Yes | Yes |
| `/admin/categories` | `AdminCategories` | Yes | Yes |
| `/admin/business-themes` | `AdminCategories` | Yes | Yes |

> **Naming note (2026-03-17)**: The active specification term is **Category**, but some as-built React component and route names still use `BusinessTheme` / `business-themes`. Those names are retained here only to describe the current code structure.
| `/workflow` | `WorkflowDashboard` | Yes | Yes |
| `/workflow/builder` | `WorkflowBuilder` (React Flow canvas) | Yes | Yes |
| `/workflow/workbench/:instanceId` | `WorkflowWorkbench` | Yes | Yes |

### Workflow UX Note

The intended workflow operating model is **process-first**, not action-bound:

- process workflows are launched from the workflow area of the SPA, not from action creation
- the intended model does not require a new dedicated process-start page beyond the existing workflow area
- actions and workflow steps may both be visible to a user on the same dashboard, but should be presented in separate panels rather than merged into one list by default
- examples include ECO, ID creation, and other request/process workflows
- action detail pages may show linked workflow instances where applicable, but that is a secondary compatibility pattern rather than the primary UX
- the current implementation still persists request-type workflow launches through a supporting action record, but the SPA should route users into the workflow workbench as the primary execution surface

### Layout Nesting

```
<Routes>
  /login → <Login />                     (no layout)
  <AuthenticatedLayout>                   (AppLayout with navbar/main content)
    / → redirect to /dashboard/personal
    /dashboard/* → <ProtectedRoute>
    /actions/* → <ProtectedRoute>
    /meetings/* → <ProtectedRoute>
    /admin/* → <ProtectedRoute>
    /workflow/* → <ProtectedRoute>
    ...
  </AuthenticatedLayout>
</Routes>
```

All authenticated pages are **lazy loaded** using `React.lazy()` + `<Suspense>` with a spinner fallback.

Detail-page navigation rule (SPA UX):
- `ActionDetail` and `DecisionDetail` expose a Back button that navigates to browser history (`navigate(-1)`) when available, with deterministic fallbacks (`/actions` and `/decisions`) when no prior in-app history exists.

---

## 5. Authentication Flow

### Token Storage

| Token | Storage | Lifetime |
|-------|---------|----------|
| Access token | `sessionStorage` | Short-lived (configurable) |
| Refresh token | `sessionStorage` | Longer-lived |
| User object | `sessionStorage` (JSON) | Mirrors access token lifecycle |

> **Design note**: `sessionStorage` was chosen over `localStorage` for security (clears on tab close). Not using HTTP-only cookies because the SPA needs to attach the token to API requests.

### Auth Flow

1. **Login**: `POST /api/auth/login` → receives `access_token`, `refresh_token`, `user` → stored in sessionStorage + React state
2. **API requests**: Axios request interceptor injects `Authorization: Bearer <access_token>` on every request
3. **Token refresh**: Axios response interceptor catches 401 → attempts `POST /api/auth/refresh` with refresh token → retries original request
4. **Refresh failure**: Clears sessionStorage → redirects to `/login`
5. **Logout**: `POST /api/auth/logout` (blacklists token) → clears state → redirect to `/login`

### Auth Context (`AuthContext.tsx`)

Provides:
- `user: User | null` — current user object
- `isAuthenticated: boolean` — derived from user presence
- `login(username, password)` — async login flow
- `logout()` — clear tokens + redirect
- `isLoading: boolean` — true during initial session restore

---

## 6. Data Fetching Patterns

### API Client (`lib/api.ts`)

- Axios instance with `baseURL: ''` (same-origin)
- 30s timeout
- Request interceptor: injects Bearer token
- Response interceptor: auto-refresh on 401, redirect on refresh failure

### TanStack Query Usage

Pages use TanStack Query for server-state management:

```tsx
// Typical pattern in a page component
const { data, isLoading } = useQuery({
  queryKey: ['actions', filters],
  queryFn: () => api.get('/api/actions', { params: filters }).then(r => r.data.data),
})
```

---

## 7. Internationalization

### Custom `useTranslation()` Hook (`lib/i18n.ts`)

A lightweight i18n solution (~340 lines) that:
- Embeds both `en` and `zh` translation catalogs inline
- Provides `t(key)` function for string lookup
- Reads language preference from user profile or browser
- Supports namespace-style keys: `'nav.dashboard'`, `'actions.title'`, etc.

This replaces a full `react-i18next` dependency while maintaining the same `en.json`/`zh.json` key structure used by the backend.

---

## 8. Shared Components

| Component | Purpose | Used By |
|-----------|---------|---------|
| `AppLayout` | Navbar + sidebar + main content area | All authenticated pages |
| `CrudTable` | Generic table with TanStack Table (sort, filter, pagination) | Actions list, admin pages, meetings |
| `KpiCard` | Dashboard metric card (value + label + color) | Personal dashboard, category dashboard |
| `ChartPanel` | Chart.js wrapper (donut, bar, line) | Dashboards |
| `StatusBadge` | Color-coded status pill | Action lists, detail pages |
| `ConfirmModal` | "Are you sure?" dialog | Delete operations |
| `DateField` | Date input with bilingual formatting | Forms |

---

## 9. Build & Deployment

### Build Command

```bash
cd action_hub/frontend
npm run build   # vite build → dist/
```

Build output is copied to `action_hub/static/assets/` (via `xcopy` in the build script — Windows-specific; on Linux, use manual `cp -r`).

### Flask Serving

Flask serves the SPA via a catch-all route:
- `/api/*` → JSON endpoints (blueprints)
- `/*` → `static/dist/index.html` (React Router handles client-side routing)

### Development

```bash
cd action_hub/frontend
npm run dev    # Vite dev server on :5173 with HMR
```

During development, the Vite dev server proxies `/api/*` requests to the Flask backend on `:5000`.

---

## 10. Future Considerations

| Area | Current State | Potential Improvement |
|------|-------------|---------------------|
| i18n | Inline catalogs in `i18n.ts` | Migrate to `react-i18next` for namespace loading and pluralization |
| State management | TanStack Query + Context | Sufficient unless global client state grows significantly |
| Testing | No frontend tests | Add Vitest + React Testing Library |
| Error boundaries | Basic `<Suspense>` fallback | Add React Error Boundary per route segment |
| Bundle analysis | No monitoring | Add `rollup-plugin-visualizer` to track bundle size |
| Code splitting | Per-page lazy loading | Could add per-section splitting for large pages |
| Workflow canvas | React Flow (`@xyflow/react`) via WF-24 | Minimap, background patterns, panel overlays for richer UX |
