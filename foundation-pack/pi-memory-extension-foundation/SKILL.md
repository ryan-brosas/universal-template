---
name: pi-memory-extension-foundation
description: "Use when building a coding-agent dual-layer memory extension: Markdown-backed Global + Workspace memory with basename-override merge, one-level scan exclusions, tail-retained per-file truncation, three-tier budget overflow, a framed anti-injection system-prompt block, git-root workspace opt-in, a human-gated checkpoint/promote capture loop with sortable timestamped candidates, read-only cache introspection commands, and a separate interrupt-state slot."
disable-model-invocation: true
---
# Pi-Memory-Extension: Dual-Layer Markdown Memory Foundation

## Use this for
Build a coding-agent persistent-memory extension that injects human-curated Markdown knowledge into the system prompt at session start. Two layers (Global `~/.pi/memory` and Workspace `<gitroot>/.pi/memory`) are scanned, merged by basename (workspace wins), budgeted with a strict drop order (state > workspace > global), and injected behind a safety preamble so stored history never masquerades as instructions. Capture is deliberately human-gated: checkpoints stage into an unscanned inbox and only reach authoritative files via an explicit promote command. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. This repo ships NO test suite — every capsule pins behavior to exact source ranges and this run's executed Node probes (GREEN) rather than a fabricated pass.

## Load the matching source dump
- `references/dual-layer-priority-merge.md` — workspace-over-global basename override; inbox/archive/state scan exclusions; empty-file dormancy; tail-retained truncation.
- `references/tail-truncation.md` — the truncate-from-head/keep-tail primitive that preserves newest entries in over-budget files.
- `references/tiered-budget-overflow.md` — the +500 slack and state>workspace>global drop order when total injected chars exceed the cap.
- `references/workspace-sentinel-opt-in.md` — git-root anchoring + `index.md` sentinel that activates a project's memory layer.
- `references/memory-injection-block.md` — the `<pi_memory>` framed block, budget ladder, and append-only `before_agent_start` injection point.
- `references/human-curation-loop.md` — checkpoint→inbox→human-review→promote-with-provenance; separate interrupt-state file channel.
- `references/state-slot-separation.md` — `state/current-task.md` as a volatile, highest-priority channel distinct from curated knowledge.
- `references/init-idempotence-phantom-config.md` — create-only-if-absent bootstrap; the dead `priority`/`globalAlwaysInject` config knobs.
- `references/observability-command-trio.md` — read-only `/memory:status` + `/memory:list` cache introspection; the registered-no-op `agent_settled` boundary marker.
- `references/checkpoint-timestamp-encoding.md` — replace-then-slice ISO stamping that makes checkpoint filenames sortable and filesystem-safe.
- `references/entry-format-social-contract.md` — the design.md entry vocabulary (`status`/`supersedes`/`confidence`) enforced by convention, not code.
- `references/tryread-null-contract.md` — the absence-is-null total reader every optional-file decision routes through.
- `references/typebox-command-schemas.md` — TypeBox `parameters` schemas as documentation-first argument contracts; cast-not-trust handlers.
- `references/extension-bootstrap-closure-state.md` — default-export factory + per-instance closure state; real vs phantom lifecycle surfaces.
- `references/package-manifest-extension-registration.md` — `pi.extensions` discovery key, files allowlist, host-provided typebox trap.
- `references/pipeline-entry-data-model.md` — the dual `content`/`injected` entry record and cache envelope flowing through scan→merge→budget.

## Capsule map
- **Layer merge** — `dual-layer-priority-merge.md`: `scanDir`/`loadLayer`/`mergeLayers` — one-level scan skipping dotfiles + inbox/archive/state; zero-byte placeholders dormant; basename-keyed whole-file override with workspace always winning.
- **Per-file budget** — `tail-truncation.md`: `truncateContent` — over-budget files drop the HEAD and keep the tail (newest), with a loud `... [truncated, tail retained]` marker.
- **Total budget** — `tiered-budget-overflow.md`: `buildMemoryBlock` — +500 slack fast-path; on overflow keep state+workspace verbatim, head-truncate ONLY global with an HTML comment marker.
- **Workspace opt-in** — `workspace-sentinel-opt-in.md`: `findGitRoot` + `index.md` sentinel — workspace layer activates only when the sentinel exists, anchored to the git root (not cwd).
- **Injection** — `memory-injection-block.md`: `<pi_memory>` framed block + `before_agent_start` — append-only systemPrompt mutation; identical safety preamble on BOTH render paths.
- **Capture loop** — `human-curation-loop.md`: `/memory:checkpoint` + `/memory:promote` — structure-only templates into unscanned inbox; allowlisted append-with-provenance + inbox delete; `agent_settled` is an intentional no-op.
- **Interrupt state** — `state-slot-separation.md`: `state/current-task.md` — separate global-only channel, top injection tier, clear-to-empty not delete.
- **Bootstrap** — `init-idempotence-phantom-config.md`: `/memory:init` — create-if-absent placeholders, refuse-on-existing workspace; `priority`/`globalAlwaysInject` are declared-but-never-read.
- **Observability** — `observability-command-trio.md`: `/memory:status` + `/memory:list` + `agent_settled` — cache-only read-only reporting with distinct not-loaded vs loaded-empty states; the empty turn-end hook documents "no automatic writes".
- **Checkpoint naming** — `checkpoint-timestamp-encoding.md`: `/memory:checkpoint` filename ladder — ISO stamp with `:`/`.` → `-` replace BEFORE 19-char slice; lexicographic order == chronological order.
- **Docs contract** — `entry-format-social-contract.md`: design.md entry fields (`status`/`valid_from`/`supersedes`/`confidence`/`verified`) — a social contract no code parses; keep convention-only or validate deliberately.
- **Null reader** — `tryread-null-contract.md`: `tryReadFile` :75–81 — every read failure ⇒ `null`; sentinel opt-in, init idempotence, and state load all key off this one error boundary.
- **Typed commands** — `typebox-command-schemas.md`: `Type.Object` parameters at :372/:535 — schema descriptions are the usage docs, handlers still cast (`args.scope as string`) with explicit defaults; typebox is host-provided.
- **Extension shell** — `extension-bootstrap-closure-state.md`: default-export factory :235 + closure `config`/`cache`; dead `ExtensionContext` import; `session_shutdown` documented in design.md:348 but unregistered (real surface = exactly 3 events + 7 commands).
- **Manifest** — `package-manifest-extension-registration.md`: `pi.extensions ["./pi-memory.ts"]` discovery, 4-file allowlist, node >=20, zero declared deps.
- **Data model** — `pipeline-entry-data-model.md`: `MemoryFileEntry{relPath,content,injected,source}` + `MemoryCache{globalRoot,workspaceRoot|null,files,stateContent}` — dual copies defer truncation and keep observability honest.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Re-read the cited `pi-memory.ts` ranges at port time — there is no upstream test suite to re-run.

## Provenance
pi-memory-extension (MIT), `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory project `pi-memory-extension` (71 nodes / 88 edges, FULL mode, zero parse_partial/skipped, coverage `no_recorded_issue` on all cited paths, indexed 2026-08-23). No upstream test suite; behavior pinned by direct-source Node probes (23 assertions GREEN on Node v26.7.0 at pass 1; 10 more GREEN at pass 2) plus whole-file reads. Pass 2 ([DONE:203]) re-read all 597 lines at unchanged HEAD; citation-vs-inventory grep exposed the observability trio (:288-368) and checkpoint stamp (:500-503) as uncited seams, and the design.md entry-format contract (:170-196) as an unmined docs plane. Pass 3 (leaf-local audit, recorded only in capsules) executed the `/tmp/piext-pime-pass3` probe battery and repaired two never-executed-probe claims ([DONE:311]/[DONE:447] erratum class). Pass 4 (2026-08-26, work record `inspo/pi-memory-extension-work/`) closed line-level citation coverage: full node enumeration (8 functions / 3 interfaces, has_more=false), whole-file reads of package.json + README + design.md, and mined the last uncited planes — tryReadFile :75-81 (graph hotspot #1), TypeBox parameter schemas :372/:535, bootstrap/closure-state :235-242 with phantom `ExtensionContext` import and phantom documented `session_shutdown` event, manifest `pi.extensions` plane, entry data model :39-56 — plus a docs-drift appendix in tiered-budget-overflow (README:100/design.md:319 say overflow truncates global "from the tail"; code :224-226 keeps HEAD via `slice(0, remaining)`).

## Full view (memory graph)
Revalidate `pi-memory-extension` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph resolves 8 functions (`findGitRoot`, `tryReadFile`, `scanDir`, `truncateContent`, `loadLayer`, `mergeLayers`, `buildMemoryBlock`, `handler`); command handlers sit below symbol granularity — confirm against raw source ranges.

## Boundaries
Adopt the basename override, one-level scan exclusions, tail-retained truncation, three-tier budget drop order, framed injection, git-root sentinel opt-in, and human-gated capture loop. Adapt budgets (`maxFileChars` 4000 / `maxTotalChars` 8000), event names, and directory taxonomy to host conventions. Omit the phantom `priority`/`globalAlwaysInject` config knobs (or implement them for real), the dead `ExtensionContext` import, the unregistered `session_shutdown` event (docs-only), Pi-specific `ctx.ui.notify` plumbing, and any auto-distillation — the no-auto-write stance is the design, not a gap. The entry-format vocabulary is convention-only upstream: adopt the fields as schema, but choose consciously between zero-parser (convention) and validated frontmatter — never half-implement.
