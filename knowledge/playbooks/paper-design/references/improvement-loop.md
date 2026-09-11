# Improve the Figma → Paper workflow from evidence

Use this after a meaningful transfer failure, a relevant Paper upgrade, or a user
request to improve the process. This is an on-demand maintenance loop, not a
background watcher or permission to change live design files unattended.

## Recheck the capability that might remove work

Read the relevant page from `index.md`, then the [build log](https://paper.design/build-log).
Discover current tool descriptors and the installed guide only for that operation.
Keep three labels separate: **documented**, **schema-inspected**, **runtime-tested**.
Roadmap items and successful transport calls are not runtime proof.

Useful changes found in the reviewed release notes:

| Release | Opportunity | Small decisive experiment |
|---|---|---|
| April 2026 | Snapshot produces editable layers from websites; MCP reparent/order tools | Capture one real coded component; inspect content/assets and compare the render |
| May 2026 | Direct Figma paste including SVG/images | Compare paste+repair against reconstruction on the same source frame |
| May 2026 | Snapshot OpenType features/full-page capture | Check a known feature-dependent text sample and its computed font/render |
| June 2026 | Token MCP creation and theme copy; negative gaps; vector path editing | Transfer an alias pair and overlapping row; inspect bindings, spacing, and editable paths |
| August 2026 | Theme-tab creation, typography dropdown tokens | Create/apply one token in a disposable file; inspect actual usage |
| August 2026 | Pasted Figma slots, flex wrapping | Paste a slotted component; change content length and frame width; inspect children and wrapping |
| August 2026 | Multi-file/background-tab agents, token SVG/PDF export fixes | Confirm explicit file targeting; export a token-bound fixture and inspect colors |

Do not infer full component linkage from slots, native modes from Theme UI, or
cross-file synchronization from token copy. `index.md` records known documentation
conflicts so a stale guide does not reintroduce literal-only theme transfers.

## Compare one representative slice

Choose an existing source frame that exercises the current problem. Keep source
node, selected mode, viewport, fonts/assets, and acceptance criteria identical for
the comparison. Use approved disposable destination artboards/files, never global
experimental recoloring of a shared product theme.

For import-route comparison:

1. Measure the current reconstruction route, or use recent comparable evidence.
2. Try direct paste plus targeted repairs on the same frame.
3. Apply the same structural and visual checks to both, using the existing Pencil
   manifest gate and saved renders rather than introducing another fidelity checker.
4. Count repair edits, tool calls/time where available, missing assets/hidden nodes,
   lost bindings, and remaining visual differences. Compare editability as well as
   pixels. Do not call it faster without comparable measurements.

Useful optional fixture cases: aliased color tokens, spacing/radius/type tokens,
image fill, SVG with instance color override, mask, rich text, slot content,
negative gap, long label, and narrow/wide frames. Pick the smallest subset that can
catch this failure; no giant mandatory matrix on every ordinary task.

For theme changes, separately inspect stored variable references and consumer
propagation (including alias consumers). For a future native mode feature, verify
actual switching and scope inheritance before removing preview workarounds.
For structural reuse, test layout/anatomy propagation separately from token changes.

## Fix one owner, not every symptom

| Finding | Canonical destination |
|---|---|
| New Paper feature / changed import limit | Matching reference in this skill, with source and review date |
| Figma identity, mode, or binding transfer policy | `../../pencil/references/tokens.md` |
| Source layout / visual mismatch | Existing Pencil layout/fidelity references or its regression fixture |
| Duplicated structure / content fitting | `../../paper-component-consistency/README.md` and existing owners |
| Product token values / intended variants | The consuming project's code/theme/component owner |
| Repeatable exact regression | Existing targeted test or gate, if it earns maintenance cost |

Persist only evidence that saves future work: a changed capability with source/date,
a reproduced failure and accepted fix, or a minimal fixture in the existing project.
Do not copy raw session logs into skills or create a new synchronization registry.
If the experiment does not beat the current path, retain the current path and record
only an expensive-to-rediscover limitation. Proposals remain proposals until tested.

## Skill maintenance acceptance

When refreshing these notes, rediscover `/docs` URLs from the sitemap, hub, and
`llms.txt`; read changed/new pages and update the coverage table. Keep runtime
claims tied to actual observations. Check links and the catalog after edits using
`../../writing-skills/README.md`. No scheduled poller or automatic skill rewrite is
installed by this workflow.
