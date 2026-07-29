# design-sync

Publishes the Wayfinder design system to the Claude Design project so that UI
generated on claude.ai comes out on-brand — and, because it is generated from
this repo rather than hand-kept, does not quietly drift from it.

```bash
python3 scripts/design-sync/build.py                      # -> dist/
LD_LIBRARY_PATH=$HOME/.local/chromium-libs \
  python3 scripts/design-sync/rendercheck.py              # 21 screenshots + checks
# then upload dist/ with the DesignSync tool (finalize_plan → write_files)
```

Project: **Wayfinder DS** · `359f65c8-9be2-406b-af60-0b9f37e29569`

| File | Role |
|---|---|
| `extract.py` | Pulls `server.py STYLE`, `services/design.py DEMO_CSS` and COLOR_TOKENS |
| `components.py` | The 21 cards — markup and the rules that go with each |
| `build.py` | Emits `dist/` (styles + patterns + preview CSS, components, guidelines) |
| `rendercheck.py` | Screenshots every card; flags blank, thin, and light-pane-not-scoped |

`dist/` and `shots/` are generated and git-ignored. Run this after any change to
the tokens or the pattern layer — the app is the source of truth, never `dist/`.

## Things that bite

- The card index comes from the first-line `<!-- @dsCard group="…" -->` comment;
  no explicit registration needed.
- The Pretendard `@import` is stripped — the design pane blocks the fetch.
- Light theme lives under `:root[data-theme="light"]`, which a pane cannot opt
  into, so `build.py` re-emits the same declarations under `.theme-light`.
- Preview-only classes are `dsx-` prefixed so they can never collide with the
  product's; the demos themselves use real product class names on purpose.
- `DesignSync.finalize_plan` requires `deletes` even when empty (`deletes: []`).
