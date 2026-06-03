# ActionHub — Performance Optimisation Specifications

> **Status**: ⚠️ ARCHIVED (2026-03-14)  
> **Reason**: All implementation details here (HTMX fragment caching, Jinja2 compression, server-rendered partial updates) were retired during SEP-4. The frontend is now a React 18 SPA served from `static/dist/`. Kept for historical reference only.  
> **Replacement**: A modern React SPA performance spec will be created when needed.  
> **Original level**: L4 — Physical / Implementation  
> **Original source**: R12_performance_optimisation.md (also archived)

---

## 1. P1 — Static Asset Caching

### 1.1 Flask send_file configuration

Override Flask's default static file handler in `actionhub/__init__.py` inside `create_app()`:

```python
from datetime import timedelta

app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=1)
```

For fine-grained control per folder, use an `after_request` hook:

```python
import re

@app.after_request
def set_cache_headers(response):
    path = request.path
    if path.startswith("/static/vendor/"):
        response.cache_control.public = True
        response.cache_control.max_age = 31_536_000   # 1 year
        response.cache_control.immutable = True
    elif re.match(r"^/static/(css|js|img)/", path):
        response.cache_control.public = True
        response.cache_control.max_age = 86_400        # 1 day
    elif path.startswith("/api/"):
        response.cache_control.no_store = True
    return response
```

### 1.2 Cache-busting for app CSS/JS

In `config.py` add:

```python
ASSET_VERSION = "2.4"   # bump on each deploy
```

In `actionhub/__init__.py` expose it to all templates:

```python
@app.context_processor
def inject_globals():
    return {
        "asset_v": app.config.get("ASSET_VERSION", "1"),
        # ... existing injected globals
    }
```

In base template (`templates/base.html`):

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}?v={{ asset_v }}">
<script src="{{ url_for('static', filename='js/app.js') }}?v={{ asset_v }}"></script>
```

---

## 2. P2 — HTTP Response Compression

### 2.1 Dependency

```
flask-compress==1.17
```

Add to `requirements.txt`.

### 2.2 Activation in `actionhub/__init__.py`

```python
from flask_compress import Compress

_compress = Compress()

def create_app(config=None):
    app = Flask(__name__)
    # ... existing config ...
    _compress.init_app(app)
    # ...
```

### 2.3 Configuration in `config.py`

```python
# Compression
COMPRESS_MIMETYPES = [
    "text/html",
    "text/css",
    "application/javascript",
    "application/json",
]
COMPRESS_MIN_SIZE = 500     # bytes — do not compress tiny responses
COMPRESS_LEVEL    = 6       # gzip level 1-9; 6 = good balance speed/ratio
```

---

## 3. P3 — HTMX Partial Updates

### 3.1 HTMX library

Use the vendored copy (no CDN dependency):

```
static/vendor/htmx/
    htmx.min.js          # v2.x
```

Add to `requirements.txt` comment block (manual download, not pip):

```
# HTMX v2.x — place htmx.min.js in static/vendor/htmx/
```

Include in `templates/base.html` before closing `</body>`:

```html
<script src="{{ url_for('static', filename='vendor/htmx/htmx.min.js') }}?v={{ asset_v }}"></script>
```

### 3.2 Backend detection pattern

Every HTMX-enabled route uses this helper:

```python
# actionhub/utils/htmx.py

from flask import request

def is_htmx() -> bool:
    """Return True when the request was initiated by HTMX."""
    return request.headers.get("HX-Request") == "true"
```

Route pattern (example — action list):

```python
from actionhub.utils.htmx import is_htmx

@bp.route("/")
@login_required
def list_actions():
    actions = service.list_actions(filters=request.args)
    if is_htmx():
        return render_template("actions/partials/table.html", actions=actions)
    return render_template("actions/list.html", actions=actions)
```

### 3.3 Fragment template location

```
actionhub/
  templates/
    actions/
      list.html                  # full page (existing)
      partials/
        table.html               # <tbody> fragment only
    dashboard/
      topic.html                 # full page (existing)
      partials/
        action_cards.html        # card container fragment
      team.html
      partials/
        action_rows.html
    meetings/
      detail.html                # full page (existing)
      partials/
        comment_list.html        # comment list fragment
```

### 3.4 Action list — filter form (P3 priority 1)

**`templates/actions/list.html`** filter form element:

```html
<form id="filter-form"
      hx-get="{{ url_for('actions.list_actions') }}"
      hx-target="#action-table-body"
      hx-swap="innerHTML"
      hx-trigger="change from:select, change from:input[type=date]"
      hx-indicator="#spinner">

  <select name="status">...</select>
  <select name="priority">...</select>
  <!-- etc. -->
</form>

<div id="spinner" class="htmx-indicator spinner-border spinner-border-sm"></div>

<table>
  <thead>...</thead>
  <tbody id="action-table-body">
    {% include "actions/partials/table.html" %}
  </tbody>
</table>
```

**`templates/actions/partials/table.html`** — rows only:

```html
{% for action in actions %}
<tr>
  <td>{{ action.act_ref }}</td>
  <td>{{ action.act_title }}</td>
  ...
</tr>
{% else %}
<tr><td colspan="8" class="text-center text-muted">No actions found.</td></tr>
{% endfor %}
```

### 3.5 Comment submission — out-of-band swap (P3 priority 4)

```html
<!-- Comment form -->
<form hx-post="{{ url_for('actions.add_comment', action_id=action.act_id) }}"
      hx-target="#comment-list"
      hx-swap="innerHTML"
      hx-on::after-request="this.reset()">
  <textarea name="body" required></textarea>
  <button type="submit">Add comment</button>
</form>

<div id="comment-list">
  {% include "meetings/partials/comment_list.html" %}
</div>
```

### 3.6 Graceful degradation

All forms **MUST** specify `method` and `action` attributes so they work without JavaScript:

```html
<form method="get" action="{{ url_for('actions.list_actions') }}"
      hx-get="{{ url_for('actions.list_actions') }}"
      hx-target="#action-table-body"
      hx-swap="innerHTML">
```

When HTMX is absent (JS disabled), the standard GET/POST executes and the route returns the full
page template (the `is_htmx()` check returns `False`).

### 3.7 Loading indicator CSS

Add to `static/css/main.css`:

```css
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { display: inline-block; }
```

---

## 4. Rollout Order

| Step | Task | Files touched |
|------|------|---------------|
| 1 | Add `flask-compress`, activate in `create_app()` | `requirements.txt`, `__init__.py`, `config.py` |
| 2 | Add `after_request` cache header hook | `__init__.py` |
| 3 | Add `ASSET_VERSION` + `asset_v` context processor | `config.py`, `__init__.py` |
| 4 | Update `base.html` with `?v={{ asset_v }}` and htmx script tag | `templates/base.html` |
| 5 | Create `actionhub/utils/htmx.py` | new file |
| 6 | Download HTMX and place in `static/vendor/htmx/` | manual |
| 7 | Refactor action list route + create `partials/table.html` | `actions/routes.py`, new partial |
| 8 | Refactor business theme dashboard + `partials/action_cards.html` | `dashboard/routes.py`, new partial |
| 9 | Refactor comment submission | `actions/routes.py`, new partial |

Each step is independently deployable and testable.
