# SubFlo Dashboard Design System

No Tailwind — plain CSS + CSS custom properties (design tokens). Responsive with 4 breakpoints.

---

## 1. Architecture

| File | Purpose |
|------|---------|
| `globals.css` | Inter font import, `:root` tokens (colors, spacing, radius, typography, layout vars) |
| `styleguide.css` | Theme overrides via `data-*` attributes (spacing, colors, radius modes) |
| `design-system.css` | Reusable components: modals, buttons, forms, data tables, panels |
| `dashboard.css` | Shell layout (`.shell`, `.sidebar`, `.header`, `.right-bar`), dashboard grid rows, cards, table, bar chart, donut chart, responsive rules |
| `custom.css` | App-specific tweaks (logo, hover effects) |

---

## 2. Design Tokens (`:root` in `globals.css`)

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--colors-background-1` | `#fff` | Page background |
| `--colors-background-2` | `#f9f9fa` | Panels, right-bar |
| `--colors-background-4` | `#edeefc` | Icon bg (bug) |
| `--colors-background-5` | `#e6f1fd` | Metric cards |
| `--colors-black-100` | `#000` | Primary text |
| `--colors-black-40` | `rgba(0,0,0,0.4)` | Secondary text |
| `--colors-black-20` | `rgba(0,0,0,0.2)` | Borders |
| `--colors-black-10` | `rgba(0,0,0,0.1)` | Light borders |
| `--colors-black-4` | `rgba(0,0,0,0.04)` | Subtle fills |
| `--colors-labels-secondary` | `rgba(60,60,67,0.6)` | Inactive tags |

### Typography (Inter)

| Scale | Size | Weight | Line height |
|-------|------|--------|-------------|
| `--14-regular-*` | 14px | 400 | 20px |
| `--14-semibold-*` | 14px | 600 | 20px |
| `--12-regular-*` | 12px | 400 | 16px |
| `--24-semibold-*` | 24px | 600 | 32px |

### Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--gap` | 18px | Grid row gap |
| `--sidebar-w` | 212px | Sidebar width |
| `--rightbar-w` | 260px | Right bar width |

### Spacing & Radius

See `globals.css` for full list. Theme overrides (expanded, condensed) in `styleguide.css`.

---

## 3. Shell Layout

```
.shell (flex row, min-height 100vh)
├── .sidebar (sticky, 212px, border-right)
└── .main (flex: 1, column)
    ├── .header (sticky top, breadcrumb + search + icons)
    ├── .page-title-row (title + "Today" button)
    └── .content (flex row)
        ├── .dashboard (flex: 1, column, gap 18px)
        │   ├── .row-stats (flex row: card-spend + mini-cards + renewals)
        │   ├── .row-mid (flex row: subscriptions table)
        │   └── .row-bottom (flex row: bar chart + donut)
        └── .right-bar (260px, notifications)
```

---

## 4. Components

### Stat Cards (`.card-spend`, `.mini-card`)

- Background: `--colors-background-5`
- Border-radius: 20px
- Padding: 20px
- `.card-spend`: fixed 280px width; label + value + optional change line + decorative gradient
- `.mini-card`: flex 1 1 0, stacked in `.mini-cards`

### Panel (`.panel`)

- Background: `--colors-background-2`
- Border-radius: 20px
- Padding: 20px
- Title: `.panel-title` (14px semibold)

### Table (`.table-wrap`)

- Flex columns: `.col-name` (flex), `.col-price` (90px), `.col-date` (100px), `.col-amt` (110px)
- Header: `.th` — 40px, bottom border, 12px muted text
- Cell: `.td` — min 46px, 12px text
- `.name-cell`: avatar square + name

### Upcoming Renewals (`.panel.renewals`)

- Always in `.row-stats` (inline with cards)
- Tags: `.tag.active` / `.tag.inactive`
- Groups: `.group-label` + `.renewal-items`
- Items: `.bar` (6×46px accent bar) + `.renewal-card` (avatar + name + price)
- Bar colors: `.bar-green` (#71dd8c), `.bar-teal` (#6be6d3), `.bar-blue` (#7dbbff)

### Bar Chart (`.chart-wrap`)

- Y-axis: `.chart-y` (4 labels, flex column)
- Grid: `.chart-grid` with repeating gradient gridlines
- Bars: `.chart-bars` > `.bar-group` > 2× `.bar-col` (light bg + solid fg)
- Labels: `.chart-labels` (flex, space-around)

### Donut Chart (`.donut-wrap`)

- SVG 120×120 with stroke-dasharray segments
- Legend: `.donut-legend` > `.legend-row` (dot + label + value)

### Notifications (`.right-bar`)

- `.notif-item`: icon (`.notif-icon.bug` / `.user` / `.sub`) + text (`.title` + `.time`)

---

## 5. Responsive Breakpoints

| Width | Changes |
|-------|---------|
| ≤1200px | Right bar hidden |
| ≤960px | `row-mid`, `row-bottom` stack; renewals + donut full width |
| ≤720px | Sidebar hidden; `row-stats` stacks; `card-spend` full width; mini-cards go horizontal |
| ≤480px | Header + dashboard padding reduced; search box hidden |

---

## 6. Data Flow (Django View → Template)

| Context Variable | Template Usage |
|-----------------|----------------|
| `monthly_spend` | Card-spend value |
| `monthly_spend_change_percent` | "+X% more than last month" |
| `total_active_trial_subscriptions` | Free Trials mini-card |
| `total_active_subscriptions` | Subscriptions mini-card |
| `subscriptions` | All Subscriptions table rows |
| `upcoming_renewals_grouped` | Renewal groups (label + subs) |
| `chart_months` | Bar chart bars (label, heights, colors) |
| `chart_y_labels` | Bar chart Y-axis labels |
| `categories` | Donut segments (label, color, dash_length, dash_offset, amount) |
