---
title: gpuix-hit-testing
summary: "Use when a GPUIX native control is only clickable on glyphs — list cards or header IconButtons with a transparent fill — or a parent scroller stops receiving wheel after a hit-target fix; choose an opaque in-flow fill over pointerEvents auto."
kind: playbook
---

# GPUIX hit testing

GPUI only hit-tests elements that own a hitbox. CSS intuition is wrong here:
making a list row `pointerEvents: "auto"` does not just enlarge the click
target. It **occludes** (`BlockMouse`), so the parent scroller never sees the
wheel.

Verify the live contract in the pinned gpuix `should_occlude` (today:
`packages/native/src/style.rs`) before treating this table as current.

## Decision

| What you observe | Usual cause | Do this |
|---|---|---|
| Clicks land only on text/icons | In-flow view with no fill, or `#00000000` / `transparent` | Put `onClick` on the control and give it an **opaque** in-flow fill (match the parent background so it is invisible). Leave `pointerEvents` **unset**. Header `IconButton`s with `colors.transparent` are the same bug as list cards. |
| Wheel over the row no longer scrolls the list | `pointerEvents: "auto"` on a list child | Remove `auto`. Keep the opaque fill. That path is `BlockMouseExceptScroll`. |
| Overlay is visible but clicks pass through | Overlay has `pointerEvents: "none"`, or is transparent and in-flow | Decorative layer: keep `none`. Clickable overlay: opaque fill or `auto` **only if it should steal the wheel** (menus, modal chrome). |
| Absolute/fixed layer steals pan/scroll | Position absolute/fixed occludes unless `none` | Decorative: `none`. Interactive overlay that must not scroll the canvas: `auto`. |

`pointerEvents: "none"` never gets a hitbox. Unset + transparent in-flow also
gets none, so padding around glyphs is dead. Unset + opaque in-flow fill is the
list-row default.

## Sequence

1. Put the handler on the full row, not a nested `<text>`.
2. Give that row an opaque fill. Do not set `pointerEvents: "auto"` inside a
   native virtual list.
3. Give small inner controls (snooze, close) their own opaque fill so they are
   the topmost hitbox. GPUIX click payloads have no `stopPropagation`.
4. Confirm wheel over empty padding still moves the parent list, then confirm a
   click off the glyphs still fires the row.

## Boundaries

- HTML/CSS hit testing is a different model (`frontend-ui-implementation`).
- Lag, launcher identity, and DE theming stay in
  [native-desktop-feel](../native-desktop-feel/README.md).
- Verify which artifact the desktop preview actually loaded before reinstalling
  or restarting. Follow
  [runtime-artifact-provenance](../runtime-artifact-provenance/README.md) for
  identity checks, restart approval and verification through the user's launcher.

## Verification

Wheel over row padding scrolls the list. Click on that padding activates the
row. Inner controls do not also activate the row. The pinned gpuix
`should_occlude` still matches the table.

## References

N/A; confirm `should_occlude` in the pinned gpuix source when the pin moves.
