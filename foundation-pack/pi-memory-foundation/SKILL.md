---
name: pi-memory-foundation
description: "Use when building a coding-agent persistent-memory extension: plain-Markdown memory with timestamp comments, line-preserving scratchpad mutations, forget/restore with durable recovery records, KV-cache-stable context snapshotting, and qmd-powered keyword/semantic/deep search."
disable-model-invocation: true
---
# Pi-Memory: Agent Persistent-Memory Extension Foundation

## Use this for
Build a coding-agent persistent-memory extension: a plain-Markdown memory system (MEMORY.md + SCRATCHPAD.md + daily/YYYY-MM-DD.md logs) with invisible timestamp comments, line-preserving scratchpad mutations that never delete hand-written notes, forget/restore backed by durable recovery records, a byte-stable KV-cache snapshot of injected context, and qmd-powered keyword/semantic/deep search that self-heals missing embeddings. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. The index was regenerated in FULL mode (2026-08-22) — tests are graph-resident, so probes pin on-disk test lines directly.

## Load the matching source dump
- `references/paths-and-dates.md` — local-calendar date helpers, memory-dir resolution, and daily-path validation.
- `references/preview-truncation.md` — the line/char-bounded, mode-aware preview and context-section builders that keep injected context within budget.
- `references/scratchpad.md` — line-preserving scratchpad parse/serialize/add/toggle/clear-done mutations.
- `references/forget-restore.md` — block-aware forget with durable recovery records and idempotent restore.
- `references/context-builder.md` — the priority-ordered memory context builder with per-section and overall char caps.
- `references/exit-summary.md` — the gated, timeout-bounded auto exit-summary that writes only real content to the daily log.
- `references/qmd-transport.md` — the qmd CLI wrapper: Windows shim bypass, ANSI stripping, JSON parsing, and collection setup.
- `references/qmd-search.md` — keyword/semantic/deep search modes, result shaping, embedding self-heal, and limit clamping.
- `references/qmd-lifecycle.md` — detect/embed/update scheduling with TTL caching, in-flight dedup, and background modes.
- `references/snapshot.md` — the KV-cache-stable memory snapshot that keeps the system prompt byte-stable across turns.
- `references/tool-surface.md` — the six memory tools + status doctor and the seven lifecycle hooks that wire it into Pi.
- `references/test-harness.md` — mock ExtensionAPI, temp-dir, and execFile-swap patterns enabling zero-dependency unit testing.
- `references/test-scope-guard.md` — meta-tests turning repository package dependencies, CI, and workflows into failing assertions.
- `references/eval-recall-ab-design.md` — the two-arm A/B harness proving selective injection improves recall (same prompt, env-only differential).
- `references/live-cli-eval-isolation.md` — driving the real pi CLI + live memory dir safely: b64-stdin transport, throw-salvage exec, backup/restore protocol.
- `references/compaction-cache-boundary.md` — why the pre-compaction hook refreshes the snapshot even when no handoff is written (finally-placement invariant).
- `references/selective-injection-kill-switch.md` — the `PI_MEMORY_NO_SEARCH=1` switch and the snapshot-mode interaction that silently defeats it.
- `references/install-time-dev-gate.md` — postinstall configuring dev git hooks via a dual-signal checkout gate that never touches consumer installs.
- `references/shutdown-capture-plane.md` — the observe-only Ctrl+D/`/quit` capture plane that records a typed exit-reason flag consumed once by shutdown.
- `references/shutdown-finality.md` — debounced updates during the session vs one awaited inline flush at terminal events, timer cleanup in `finally`.
- `references/status-doctor.md` — the memory_status doctor: defensive inventory snapshot, staged lazy probes, dual human/machine output, embedding self-heal.
- `references/tool-error-as-data.md` — validation/environment failures return `isError` text data instead of throwing; expected misses stay plain results.
- `references/write-echo-preview.md` — every mutating tool echoes a capped, mode-matched preview of the file it just changed so the next call plans from real state.
- `references/qmd-cache-behavior-plane.md` — deterministic TTL/dedup/seeding proofs via a counting fake execFile, negative-status seeding, and setup-writes-cache assertions.
- `references/e2e-inprocess-tool-harness.md` — replaying registration against a two-method fake host and driving production `execute()` directly, no CLI spawn.
- `references/e2e-battery-degradation.md` — tiered e2e battery: hard preflight vs optional-backend skips, whole-battery backup/restore envelope, planted-token injection asserts.
- `references/shared-io-session-helpers.md` — total optional-file reads (`null`, never throw) and 8-char session attribution stamps every plane assumes.
- `references/markdown-indexing-cycle.md` — write → explicit index refresh → tag/wiki-link keyword retrieval; syntax survives as searchable text.

## Capsule map
- **Paths & dates** — `references/paths-and-dates.md`: `PI_MEMORY_DIR` override, cross-platform home resolution, LOCAL-calendar date helpers, strict daily-date validation, `_setBaseDir` test seam.
- **Preview & truncation** — `references/preview-truncation.md`: start/end/middle line+char truncation, `buildPreview`, `formatPreviewBlock`, `formatContextSection`.
- **Scratchpad** — `references/scratchpad.md`: `- [ ] text` checklist with `<!-- ts [sid] -->` meta, line-preserving add/toggle/clear-done that never deletes unknown content.
- **Forget & restore** — `references/forget-restore.md`: `forgetBlocks` block-aware deletion (stamped entries removed as a unit), UUIDv4 recovery records written before mutation, idempotent append-only restore.
- **Context builder** — `references/context-builder.md`: scratchpad > today > search > MEMORY.md > yesterday priority, per-section caps, 16K overall cap with `[truncated]` note.
- **Exit summary** — `references/exit-summary.md`: ≥4-message gate, model override, API-key resolution, `isExitSummaryEmpty` filter, self-imposed timeout, lifecycle-transition skip.
- **qmd transport** — `references/qmd-transport.md`: `buildQmdSpawn`/`buildQmdEnv` Windows shim bypass via `resolveQmdJsPath`, ANSI CSI/OSC stripping, JSON extraction, collection/context setup.
- **qmd search** — `references/qmd-search.md`: `runQmdSearch` mode→subcommand map, `clampSearchLimit`, result shaping, `need embeddings` self-heal, `searchRelevantMemories` 3s race.
- **qmd lifecycle** — `references/qmd-lifecycle.md`: `detectQmd`/`checkCollection` TTL caching (positive 5m, negative 5s), `ensureQmdEmbed` in-flight dedup + pending queue, `scheduleQmdUpdate` 500ms debounce.
- **Snapshot** — `references/snapshot.md`: `PI_MEMORY_SNAPSHOT=stable|per-turn`, refresh on session_start/compact/long-term-write/day-rollover, byte-stable systemPrompt, dirty flag.
- **Tool surface** — `references/tool-surface.md`: memory_write/read/forget/restore/search + scratchpad + memory_status tools and the seven `pi.on` lifecycle hooks.
- **Test infrastructure** — `references/test-harness.md`, `references/test-scope-guard.md`: zero-dependency mock ExtensionAPI context, temp directory lifecycle, execFile test seams, package scope assertion gates.
- **Eval & verification plane (pass 2)** — `references/eval-recall-ab-design.md`, `references/live-cli-eval-isolation.md`: two-arm injection-effectiveness measurement over a dated corpus; live-CLI transport + backup/restore isolation protocol.
- **Lifecycle cache boundary (pass 2)** — `references/compaction-cache-boundary.md`, `references/selective-injection-kill-switch.md`: compaction-forced snapshot refresh regardless of handoff writes; the per-turn-only injection kill switch.
- **Packaging (pass 2)** — `references/install-time-dev-gate.md`: dual-signal dev-checkout gate scoping git-hook config to the source repo only.
- **Shutdown plane (pass 3)** — `references/shutdown-capture-plane.md`, `references/shutdown-finality.md`: observe-only exit-reason capture (Ctrl+D three-clause gate, user-only `/quit`) consumed once with a neutral default; debounced steady-state updates vs one awaited inline flush at terminal events.
- **Diagnostics & tool contract (pass 3)** — `references/status-doctor.md`, `references/tool-error-as-data.md`, `references/write-echo-preview.md`: defensive inventory + staged lazy probes doctor; `isError`-as-data severity taxonomy; capped mode-matched write echoes.
- **Test planes deep pass (pass 4)** — `references/qmd-cache-behavior-plane.md`, `references/e2e-inprocess-tool-harness.md`, `references/e2e-battery-degradation.md`, `references/shared-io-session-helpers.md`, `references/markdown-indexing-cycle.md`: the behavioral-proof plane for lifecycle caches; in-process tool execution without a CLI spawn; tiered battery with graceful degradation and data-safety envelope; the two total-helper contracts under everything; the tag/wiki-link indexing freshness cycle.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Each new capsule must carry Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt, Flow, Invariant, a direct-test Probe, and a `search_graph` Retrieve.

## Provenance
pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e` = base_sha); Codebase Memory project `pi-memory`, root `/mnt/hdd/utopia/inspo/pi-memory` (canonical `/mnt/hdd/utopia/inspo/pi-ecosystem/pi-memory`), FULL mode 380 nodes / 941 edges, generation 2026-08-22T23:46:09Z, zero parse_partial/skipped; `not_indexed` = `.git` only. Passes 1–3 mined against this index (pass 3 verified zero drift: local = origin = base at re-entry on 2026-08-24); the pre-drain "fast index / tests excluded" caveat is OBSOLETE. Pass 4 (2026-08-25) re-verified pin/counts at re-entry and mined the test planes: `qmd-cache-behavior-plane`, `e2e-inprocess-tool-harness`, `e2e-battery-degradation`, `shared-io-session-helpers`, `markdown-indexing-cycle`, plus a qmd-search Probe extension (timeout-flow diagnostics test :1226–1243); work record now at `/mnt/hdd/utopia/inspo/pi-memory-work/`.

## Full view (memory graph)
Revalidate `pi-memory` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. `index.ts`, all four `test/*.ts` files report `no_recorded_issue` + `metadata_match`; only `scripts/postinstall.cjs` reports `freshness: missing` (read source directly — its contract is pinned live both polarities in pass 2).

## Boundaries
Adopt the plain-Markdown memory contract, the local-calendar date helpers, the line-preserving scratchpad mutations, the block-aware forget with durable recovery records, the byte-stable KV-cache snapshot, and the qmd keyword/semantic/deep search lifecycle. Adopt from pass 3: the observe-only shutdown-capture plane, the debounce-vs-inline finality split, the never-throw doctor, the isError-as-data tool contract, and capped mode-matched write echoes. Adapt the memory directory layout, char/line caps, env-var names, qmd collection name, and the exact timestamp-comment regex to the host. Omit the Pi extension wiring (`index.ts` default export, `pi.on` hooks, `pi.registerTool` calls) and the qmd vendor integration unless a target needs them.
