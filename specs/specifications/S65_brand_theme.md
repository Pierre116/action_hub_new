# S65 — Corporate Brand Theme & UI Polish

> **Version**: v3.0  
> **Date**: March 2026  
> **Implements**: UI redesign with professional corporate identity

> **Updated**: 2026-03-14 — §1–§3 (brand colors, typography, CSS variables) remain the authoritative design tokens. §4 updated to reference React SPA files (SEP-4 retired all Jinja2 templates). Tokens are applied via Bootstrap theme overrides in `static/css/actionhub.css` and consumed by React components.

---

## §1 Brand Colors

Corporate color palette for professional use:

| Token | Hex | Usage |
|-------|-----|-------|
| `--brand-dark` | `#222222` | Navbar background, headings |
| `--brand-orange` | `#E64C00` | Accent line, CTAs, highlights, PILOT badge |
| `--brand-blue` | `#003382` | Primary buttons, links, interactive elements |
| `--brand-light` | `#F2F2F6` | Page background |
| `--brand-text` | `#222222` | Body text |
| `--brand-muted` | `#666666` | Secondary text, table headers |
| `--brand-border` | `#E0E0E0` | Card borders, dividers |
| `--brand-card` | `#FFFFFF` | Card backgrounds |

---

## §2 Typography

```css
font-family: "Montserrat", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
font-size: 0.9375rem;   /* 15px base */
line-height: 1.55;
```

- Chinese fallback: `"Noto Sans SC", serif` (via `:lang(zh)` override)
- Google Fonts loaded: `Montserrat:wght@300;400;500;600;700` + `Noto+Sans+SC:wght@400;500;600;700`

- Headings: `font-weight: 600`, `letter-spacing: -0.01em`
- Table headers: `text-transform: uppercase`, `font-size: 0.75rem`, `letter-spacing: 0.04em`
- Navbar: `font-size: 0.875rem` (14px)

---

## §3 Component Styling

### §3.1 Navbar
- Background: `--brand-dark` (#222222)
- Bottom border: `3px solid --brand-orange` (#E64C00)
- Removed Bootstrap `bg-primary` class
- PILOT badge: orange background

### §3.2 Cards
- Border: `1px solid --brand-border`
- Border-radius: `0.5rem`
- Shadow: `0 1px 3px rgba(0,0,0,.04)` → `0 2px 8px rgba(0,0,0,.08)` on hover
- Card header: `#FAFAFA` background with bottom border

### §3.3 Buttons
- `.btn-primary`: brand blue (`#003382`)
- `.btn-danger`: brand orange (`#E64C00`)
- Focus ring: `rgba(0, 51, 130, .18)`

### §3.4 Status Chips
| Status | Background | Text |
|--------|-----------|------|
| Open | `#E8EFF5` | `#003382` |
| In Progress | `#FFF3E0` | `#E64C00` |
| On Hold | `#FFF8E1` | `#F9A825` |
| Done | `#E8F5E9` | `#2E7D32` |
| Cancelled | `#F5F5F5` | `#9E9E9E` |

### §3.5 Accordion
- Active: `rgba(0, 51, 130, .06)` tinted background
- Focus: `rgba(0, 51, 130, .2)` ring

### §3.6 Scrollbar
- Width: 6px
- Thumb: `#CBD5E1` (hover: `#94A3B8`)
- Track: transparent

---

## §4 Files Changed

| File | Changes |
|------|---------|
| `static/css/actionhub.css` | Complete rewrite with CSS custom properties, brand tokens, professional typography, component polish |
| `frontend/src/components/AppLayout.tsx` | Navbar uses `--brand-dark` background + `--brand-orange` accent line; notification bell dropdown (TanStack Query polling) |
| `frontend/src/pages/meetings/MeetingDetail.tsx` | Participants list, Manage modal, Notify button — all styled with brand tokens |
| `config.py` | ASSET_VERSION bumped to 3.30 |

---

## §5 Implementation Plan (Completed)

| # | Task | Status |
|---|------|--------|
| 1 | Define corporate brand color palette | ✅ Done |
| 2 | Define CSS custom properties (--brand-*) | ✅ Done |
| 3 | Rewrite actionhub.css with brand alignment | ✅ Done |
| 4 | Update navbar (dark charcoal + accent line) | ✅ Done |
| 5 | Polish cards, tables, buttons, badges | ✅ Done |
| 6 | Add notification bell + 30s polling JS | ✅ Done |
| 7 | Create t_meeting_participant table | ✅ Done |
| 8 | Participant service + routes | ✅ Done |
| 9 | Meeting detail UI (participants + notify) | ✅ Done |
| 10 | Update spec.html to v3.0 | ✅ Done |
| 11 | Create R15 + S65 spec documents | ✅ Done |
| 12 | Bump ASSET_VERSION + restart server | ✅ Done |
