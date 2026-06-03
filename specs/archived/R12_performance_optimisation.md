# ActionHub — Performance Optimisation

> **Status**: ⚠️ ARCHIVED (2026-03-14)  
> **Reason**: All techniques in this file (HTMX partials, Jinja2 caching, server-rendered compression) were retired during SEP-4 (React SPA migration). Kept for historical reference only.  
> **Replacement**: A modern React SPA performance spec will be created when needed (code-splitting, TanStack Query cache tuning, bundle budgets).  
> **Original depends**: `R00_initial_vision.md`, `S30_physical_specs.md`  
> **Original consumed by**: `S45_performance_optimisation.md` (also archived)

---

## §1 Context & Rationale

ActionHub runs on a **single server with limited resources** (low-cost VPS or on-premise machine).
The goal is to reduce unnecessary server load without rewriting the application stack.

Three targeted optimisations are specified:

| # | Technique | Primary Benefit | Effort |
|---|-----------|----------------|--------|
| P1 | Static asset caching (Cache-Control headers) | Eliminate repeat asset downloads | Low |
| P2 | HTTP response compression (gzip/deflate) | Reduce transfer size 60–70 % | Low |
| P3 | HTMX partial updates on high-traffic pages | Replace full-page HTML round-trips with fragment responses | Medium |

> **Out of scope**: CDN, Redis caching, full SPA migration (React), database replication.

---

## §2 P1 — Static Asset Caching

### §2.1 Requirement

Static files (CSS, JavaScript, fonts, images, vendor libraries) **MUST** be served with explicit
`Cache-Control` headers so browsers do not re-request them on every navigation.

### §2.2 Cache policy

| Asset type | `Cache-Control` value | Rationale |
|---|---|---|
| Vendor libraries (`/static/vendor/`) | `public, max-age=31536000, immutable` | Never change between versions |
| App CSS / JS (`/static/css/`, `/static/js/`) | `public, max-age=86400` | May change on deploy — daily re-validate |
| Images (`/static/img/`) | `public, max-age=604800` | Weekly |
| API responses (`/api/*`) | `no-store` | Always fresh |

### §2.3 Cache-busting

App-owned CSS/JS filenames **SHOULD** include a version query string (e.g. `?v=2.4`) updated at
each release to force re-download after a deploy.

---

## §3 P2 — HTTP Response Compression

### §3.1 Requirement

All HTTP responses **MUST** be compressed (gzip preferred, deflate fallback) for content types:
`text/html`, `text/css`, `application/javascript`, `application/json`.

### §3.2 Minimum compression threshold

Responses **MUST NOT** be compressed if the body is smaller than **500 bytes** (overhead
outweighs benefit).

### §3.3 Implementation

Compression is applied transparently via a Flask extension at the WSGI middleware level; no
blueprint-level changes are required.

---

## §4 P3 — HTMX Partial Updates

### §4.1 Rationale

Full-page reloads for every filter, search, or status change cause unnecessary template rendering
and asset parsing on both server and browser. HTMX allows targeted HTML fragment responses,
keeping the SSR / Jinja2 stack intact.

### §4.2 Target pages (priority order)

| Priority | Page | Current behaviour | Target behaviour |
|---|---|---|---|
| 1 | Action list (`/actions/`) | Full reload on every filter change | Filter form triggers fragment swap of table body only |
| 2 | Category dashboard (`/dashboard/topic/<id>`) | Full reload on status filter | Fragment swap of action cards |
| 3 | Team dashboard | Full reload on filter | Fragment swap of action rows |
| 4 | Action detail — comment submission | Full page POST + redirect | Out-of-band swap of comment list only |

### §4.3 Design constraints

- Page **MUST** remain fully functional without JavaScript (graceful degradation — standard form
  POST fallback).
- HTMX **MUST NOT** be used for any operation that changes authentication state (login/logout).
- Backend routes **MUST** detect whether the request is a full-page or HTMX partial request and
  return the appropriate template or fragment.
- Fragment templates **MUST** reside in a `partials/` sub-folder inside each blueprint's template
  directory.

### §4.4 HTMX attributes (standard usage)

| Attribute | Usage |
|---|---|
| `hx-get` | Trigger a GET to a fragment endpoint |
| `hx-post` | Submit a form to a fragment endpoint |
| `hx-target` | CSS selector of the DOM element to replace |
| `hx-swap` | `innerHTML` for table bodies; `outerHTML` for card containers |
| `hx-trigger` | `change` for filter dropdowns; `submit` for forms |
| `hx-indicator` | Loading spinner element selector |

---

## §5 Non-functional Targets

| Metric | Target |
|---|---|
| Time To First Byte (TTFB) after P2 | < 200 ms (LAN) |
| Repeat page load (browser cache hit) | < 50 ms |
| Filter/search response (HTMX fragment) | < 300 ms |
| Server RAM delta from optimisations | 0 MB (no new persistent process) |
