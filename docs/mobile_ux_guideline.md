# Wayfinder Mobile UX Guideline (v1 — 2026-07-22)

Applies to every Wayfinder app. Derived from NN/g, Baymard, Material 3, Apple HIG,
WCAG 2.2, Polaris/Carbon patterns + a live audit of cardconv at 390px.
cardconv is the reference implementation; new UI work must follow this doc.

## 1. Breakpoints

| Token | Query | Meaning |
|---|---|---|
| mobile | `@media(max-width:768px)` | Phones + narrow split-screens. **Standard breakpoint for all new mobile rules.** |
| small | `@media(max-width:480px)` | Small phones — density reductions only. |

Legacy 600/640px queries keep working; migrate them to 768 opportunistically when
touching the surrounding code. Never write device-specific breakpoints.
Assume touch from 768px down: hover states must have visible non-hover equivalents.

## 2. Chrome budget (the #1 audit finding)

Total persistent chrome (sticky top + fixed bottom) ≤ **25% of viewport height**.

- Site nav: one line, always. `.nav-brand` never wraps (ellipsis). Slim padding on mobile.
- In-page pill tabs: **never wrap to 2 rows.** Horizontally scrollable
  (`flex-wrap:nowrap; overflow-x:auto`), scrollbar hidden, edge-fade mask as the
  overflow affordance, and the active tab auto-scrolled into view on load.
- Workflow/step bars, filter bars, intake sections: scroll away (not sticky) on mobile.
- Anchored content must set `scroll-margin-top` equal to the sticky stack height.

## 3. Touch targets

- Primary controls (buttons, tabs, nav links): ≥44px hit area (48px preferred).
  Grow the hit area with padding, not the glyph.
- Checkboxes/radios: ≥20px visual box **and** the whole label/leading-zone tappable.
- Icon-only buttons (×, ℹ, ⋯): keep the glyph small, extend the hit box to 44px
  via padding or `::before { inset:50% auto auto 50%; translate:-50% -50%; width:max(100%,44px); height:max(100%,44px) }`.
- Adjacent targets: centers ≥24px apart (WCAG 2.2 floor).
- All tappables: `touch-action:manipulation` + a visible `:active` state (<100ms).

## 4. Inputs & forms

- **`font-size:16px` minimum on every input/select/textarea at ≤768px** — computed
  size below 16px triggers iOS focus auto-zoom. Never "fix" with `maximum-scale=1`.
- Text inputs/selects: min-height 44px on mobile. Labels above the field; placeholder
  is example-format only, never the label.
- Money: `type="text" inputmode="decimal"` (never `type="number"`), currency symbol
  outside the field, format on blur, `font-variant-numeric:tabular-nums` for display.
- Receipt/date entry: native `input[type=date]` is fine; add Today/Yesterday quick chips
  where most entries are recent.
- Photo intake: two buttons — "Take photo" (`accept="image/*" capture="environment"`)
  and "Upload" (no capture, `multiple`). Instant client-side thumbnail preview,
  per-file remove/retake, upload in background while metadata is typed.

## 5. Tables & lists on mobile

- **Transactional rows** (act/select/open — Ledger, Review, History): card transform.
  A card shows at most: primary (merchant/title), amount (top-right, tabular-nums,
  primary weight), one secondary line, status chip. Everything else lives in the
  row detail. 10-field label:value stacks (≈700px/row in the audit) are banned.
- **Reference/comparison tables** (Keywords, rate tables): keep the grid,
  horizontal scroll inside its own `overflow-x:auto` wrapper, sticky header +
  pinned first column, cut-off column at the edge as the scroll affordance.
  The page body never scrolls horizontally.
- Row detail: full-width panel/bottom sheet on mobile (`max-height:90dvh`,
  visible ✕, back/scrim dismiss, `overscroll-behavior:contain`); deep edits → full page.
- List growth: "Load more" + "Showing X of Y". No pure infinite scroll for records.

## 6. Bulk selection & actions

- Checkboxes always visible (≥20px, padded target). No long-press-only entry.
- The bulk action bar **appears only while selection > 0**, sticky at the bottom
  (thumb zone), with count, 1–2 promoted actions, overflow for the rest, and ✕.
  Pad it with `env(safe-area-inset-bottom)`; give the list matching bottom padding.
- Destructive bulk ops: confirm or provide undo toast.

## 7. Filters, sort, search

- Mobile toolbar: search + 1–2 promoted filters visible; the rest collapse
  (accordion/sheet) behind "Filters · N" with the active count badged.
- Applied filters must stay visible when collapsed (chips or badge) — hidden active
  filters read as "my data vanished".
- Sort is a separate closed single-choice control, not a filter facet.

## 8. Overlays & keyboard

- Mobile default: bottom sheet (≤4 fields / action menus) or full-screen takeover
  (>1 text input or >4 fields). Center modals only for short blocking confirms.
- Heights in `dvh`/`svh`, never bare `100vh`. Viewport meta gains
  `interactive-widget=resizes-content` so keyboards resize the layout.
- iOS-safe body scroll lock: `position:fixed; top:-scrollY` on body, restore on close.
- Every overlay: visible close button; gestures are never the only exit.

## 9. Fixed-bottom & safe areas

- One sticky bottom bar max per screen. `padding-bottom:env(safe-area-inset-bottom)`
  on the bar, matching `padding-bottom` on the content so nothing hides beneath it.
- Floating pills (home link, theme toggle) must not cover list content:
  reserve bottom padding on the container.

## 10. Feedback & perceived speed

- Skeleton rows for list loads >300ms; spinner only for in-place micro-actions.
- Mutations: pending state within 100ms (disabled CTA + label swap); optimistic UI
  only for cheap reversible toggles — never for money-moving submits.
- Empty states come in three distinct variants: first-use (CTA), filtered-to-empty
  ("Clear filters"), and error (Retry).

## Compliance checklist (per screen, at 390px)

1. No horizontal page scroll; no wrapped tab rows; chrome ≤25% viewport.
2. All inputs ≥16px font; primary targets ≥44px; checkboxes ≥20px + padded label.
3. Cards ≤4 visible fields; detail/edit in full-width panel or sheet.
4. Bulk bar hidden until selection; sticky bottom; safe-area padded.
5. Active filters visible when collapsed; tap feedback on every control.
