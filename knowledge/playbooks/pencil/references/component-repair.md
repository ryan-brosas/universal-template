# Repairing pasted component families

Use when a Figma-to-Paper copy exists but its variants differ visibly. This is a repair procedure, not a second import pipeline.

## Scope and acceptance

Confirm live file, page, selected source IDs, and native targets. A family absent from Paper's artboard list may still exist as a top-level SVG; inspect page children before calling it missing. Preserve vectors and hidden-state semantics.

Define a bounded acceptance set: source-relative positions and dimensions, changed paints/type, preserved assets and tokens, and a fresh render of the repaired block. Reuse the project's successful helper before diagnosing the same failure again. Parameterize genuine differences rather than cloning the pipeline.

## Representative repair, then rollout

Capture the changed properties for rollback. Trace source-instance overrides, not just the base component. Test one representative variant; inspect the visible result and measured geometry before applying the same fix to matching targets. Preserve semantic colors, unrelated properties, and approved theme adaptations.

Useful failure signatures:

- **Cross-column stretching:** inspect grid spans and intrinsic width. A source HUG child accidentally spanning two tracks can stretch every matching variant. Preserve source row positions and blank tracks. Check vertical HUG separately: fixed grid tracks can stretch a 48px item to 50px even after width is repaired.
- **Nested inside strokes:** CSS borders consume layout space while Figma INSIDE strokes do not. For a solid divider or underline without conflicting effects, an inset shadow can retain its color and thickness without increasing height. Preserve existing shadows. This is not a dashed-border recipe: converting a dashed divider to a solid shadow loses fidelity. Padding compensation or a separate stroke layer needs its own canary.
- **Lost instance overrides:** an icon may retain its base 24px size instead of an overridden 20px size; a badge may retain 4px instead of 6px. Resolve canonical size tokens and verify the containing control. Recompute anchored offsets: `right = parentWidth - sourceX - childWidth`.
- **Duplicated child shadows:** remove only a proven propagated parent effect when the child has no corresponding source effect. Preserve child-owned effects. Do not erase blur or shadows merely because a screenshot looks strange.
- **Wrong text metrics:** compare actual source family, weight, line height, and spacing before forcing widths. Probe font availability and inspect rendered text. A monospace label pasted with a proportional family is not fixed by changing its container width. Do not replace a global body-font token for a local source override.

## Verification without false passes

Keep the live pre-change token snapshot and source version used by this repair. An older project-wide baseline may contain unrelated differences; classify them explicitly. An unchanged token hash supports preservation, but does not replace inspecting the relevant token definitions.

Capture the intermediate geometry baseline only after the layout repair has settled and passed. Some Paper observations in this project refreshed after a successful screenshot; this is an observation, not a guaranteed flush API. If styles report the new value but geometry still reports the old size, keep geometry pending until fresh measurements agree. Do not overwrite a failed baseline with final measurements to manufacture zero drift.

A successful style receipt proves application, not source dimensions or appearance. Preserve failed verifier results; separate stale-baseline concerns from unresolved geometry. Font availability alone does not prove rendering; a matching width alone does not prove font identity.

## When rendering fails

A timeout or black image does not identify its cause. Inspect whether a preceding mutation succeeded before retrying. Try one bounded render using a previously working target or native scale. If it still fails, follow the screenshot-session recovery procedure; avoid restarting an application with unsaved work without coordination.

Stop expanding the repair when the representative visible result cannot be checked. Record applied, structurally checked, visually pending, and untouched scope separately. User approval is useful acceptance evidence, not a substitute for an unperformed pixel comparison. If redirected, park remaining issues and follow the new scope.
