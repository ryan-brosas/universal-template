---
name: pi-upstream-foundation
description: "Use when building a coding-agent harness: agent loop modes, tool-execution ordering, compaction cut points and iterative summaries, branch summarization, lane-record session durability, LLM boundary conversion, and streaming-TUI seams."
disable-model-invocation: true
---
# Pi Upstream Foundation

## Use this for
Building or porting a coding-agent loop and its context engine: start/continue entries, parallel tool-call execution with source-order results, hybrid token estimation, safe compaction cut points, split turns, iterative summary state, branch-jump summarization, durable operation records, and the terminal-input/rendering seams that keep a TUI agent usable.

## Load the matching source dump
- `references/agent-loop-modes.md` — two entry modes; why continue-mode guards are cheap by design.
- `references/truncated-tool-batch.md` — length-capped responses fail every tool call, never execute them.
- `references/tool-execution-modes.md` — prepare sequential, execute parallel, persist in source order; terminate = unanimity.
- `references/steering-lifecycle.md` — steering drains at boundaries only; prepareNextTurn / shouldStopAfterTurn hooks.
- `references/hybrid-token-estimate.md` — provider usage as truth, char-heuristic only the trailing delta.
- `references/safe-cut-points.md` — which entries are legal compaction cuts; turn-boundary backup.
- `references/iterative-compaction-state.md` — retained tail rides on the entry; virtual reconstruction; accumulating file ledgers.
- `references/split-turn-compaction.md` — two-request handling when the budget lands mid-turn.
- `references/summary-request-isolation.md` — cacheRetention none + fresh uuidv7 session + reserve-sliced maxTokens.
- `references/structured-summary-prompts.md` — anti-continuation framing, exact sections, PRESERVE-and-ADD updates.
- `references/branch-summarization.md` — summarize only old-leaf→common-ancestor; newest-first with the 90% dense-summary rule.
- `references/session-context-assembly.md` — last-compaction-wins transform; read-time tail expansion; deferred-message drop.
- `references/llm-boundary-conversion.md` — one convertToLlm per turn; synthetic roles become user text.
- `references/lane-record-durability.md` — operation records, 0/1/2+ open-operation recovery tri-state, replay classification.
- `references/session-state-mutations.md` — one validated mutation choke point; consecutive seq, lane chaining, stats asymmetry, fork renumbering.
- `references/durable-payload-json-gate.md` — reject non-finite numbers, cycles, prototypes, symbols, accessors, sparse arrays BEFORE any write.
- `references/open-operation-admission.md` — storage-level one-open-op-per-lane guard; in-process destination claims for timestamped filenames.
- `references/jsonl-torn-tail-repair.md` — syntax-final-line truncates atomically; schema errors refuse; tmp+rename publication.
- `references/record-log-reducer.md` — pure validate-then-derive recovery: corruption taxonomy, abort queue semantics, terminal-failure attribution.
- `references/stdin-sequence-buffering.md` — per-protocol completeness classifiers; WezTerm/Kitty traps; paste-as-event.
- `references/fuzzy-scoring.md` — muscle-memory score shape; digit-swap fallback behind a handicap.
- `references/autocomplete-triggers.md` — natural-vs-forced triggers; quote-aware completion math.
- `references/streaming-markdown.md` — trim partial closing fences; conservative pending-math; wrap ANSI after width math.
- `references/alt-screen-search.md` — mapped-corpus search across wrapped lines.
- `references/alt-screen-verified-clipboard.md` — injected `copySelection(text): Promise<boolean>` beats bare OSC 52; flash success only on verified copy.
- `references/markdown-cell-sgr-reset.md` — reset SGR attributes after every non-final wrapped cell fragment; restore the cell prefix before padding.
- `references/keybinding-registry.md` — semantic action ids over raw keys.
- `references/editor-safety-seams.md` — atomic pastes, snapshot-validated suggestions, draft-preserving history.
- `references/edit-single-object-widening.md` — coerce single `{oldText,newText}` shapes into the edits array at argument-preparation; schema stays strict.
- `references/skill-declared-quiet-skip.md` — warn on declared SKILL.md failures and all read failures; quietly skip undeclared loose-markdown parse errors.
- `references/managed-install-classification.md` — when is a running Pi an installer-managed install; why inherited launcher env must never misclassify a source checkout.
- `references/staged-managed-self-update.md` — how an installation replaces itself without ever leaving a broken one active.
- `references/sqlite-fenced-writer-lease.md` — conditional-upsert lease steals expired-only and bumps a fence per takeover; stale owners can never write again.
- `references/sqlite-transactional-write-ownership.md` — serial queue → BEGIN IMMEDIATE → renew-lease-inside-the-write-transaction; losing the lease poisons the storage permanently.
- `references/sqlite-derived-branch-cache-cow.md` — materialized root→tip paths per branch_id; tips are optimistic pointers; mid-branch appends copy-on-write through seq.
- `references/sqlite-compaction-stop-window.md` — SQL stop-boundary at the last compaction entry (inclusive); decode only after window selection; chain validation catches cache drift.
- `references/sqlite-single-sequence-log.md` — one counter row per session; every mutation spends exactly one seq; lazy-decode merge pages four streams.
- `references/sqlite-lane-operation-pointer.md` — CAS on a nullable lane pointer admits at most one open operation; recovery dereferences the pointer instead of scanning.
- `references/sqlite-session-fork-renumber.md` — fork copies ids stable but renumbers seqs 1..n; stats and branch cache are recomputed, never copied.
- `references/sqlite-fts5-search-plane.md` — external-content FTS5 with insert/delete/update triggers plus a creation-time rebuild; whole-query phrase quoting before MATCH.
- `references/session-backend-conformance-harness.md` — one factory of shared test cases proves memory/JSONL/SQLite/server backends obey the same SessionStorage contract.

## Capsule map
- **Agent loop** — agent-loop-modes, truncated-tool-batch, tool-execution-modes, steering-lifecycle: AgentMessage throughout, convertToLlm once at the boundary, ordered concurrent tool batches, queue-at-boundary steering.
- **Compaction & summarization** — hybrid-token-estimate, safe-cut-points, iterative-compaction-state, split-turn-compaction, summary-request-isolation, structured-summary-prompts, branch-summarization: shouldCompact → estimate → cut → summarize → persist tail, plus branch-jump detours.
- **Session & boundary** — session-context-assembly, llm-boundary-conversion, lane-record-durability, session-state-mutations, durable-payload-json-gate, open-operation-admission, jsonl-torn-tail-repair, record-log-reducer: durable entries vs operation records, read-time rehydration, provider-legal payloads, crash-recovery tri-state, single-writer state machine, load-time triage, pure validate-then-derive recovery.
- **Terminal UX** — stdin-sequence-buffering, fuzzy-scoring, autocomplete-triggers, streaming-markdown, alt-screen-search, keybinding-registry, editor-safety-seams, alt-screen-verified-clipboard, markdown-cell-sgr-reset: input reliability, polite suggestion surfaces, streaming-tolerant rendering.
- **Tool & skill loading (drift pass 2)** — edit-single-object-widening, skill-declared-quiet-skip: argument-layer coercion that keeps published schemas strict; declaration-driven diagnostic noise.
- **Self-update & install lifecycle (drift pass 3)** — managed-install-classification, staged-managed-self-update: three-legged managed-install gate (env AND marker AND package-dir containment), stage → verify → atomic-rename → pointer-flip update pipeline under an exclusive lock.
- **SQLite session backend (pass 4)** — sqlite-fenced-writer-lease, sqlite-transactional-write-ownership, sqlite-derived-branch-cache-cow, sqlite-compaction-stop-window, sqlite-single-sequence-log, sqlite-lane-operation-pointer, sqlite-session-fork-renumber, sqlite-fts5-search-plane, session-backend-conformance-harness: the third `SessionStorage` backend as the SQL witness for the durability contracts above — fenced cross-process leases renewed inside every write transaction, a derived branch cache with copy-on-write forks and compaction stop-window reads, one total-order sequence across entries/records/lane-moves/facts, structurally-collapsed open-operation tri-state, and a shared conformance suite that keeps all backends honest.

## Extending the foundation
Add one references-file capsule per seam from `.pi/templates/foundation-capsule.md` (Source/Question, Path/Symbol, Signature, Data Shape, decisive source excerpt, Flow, Invariant, Probe, Retrieve, Verdict), add its loader line, group it in this map, and pin probes to `packages/agent/test/` / `packages/tui/test/`.

## Provenance
Indexed in Codebase Memory as `pi-upstream` (`/mnt/hdd/utopia/inspo/pi-upstream`, canonical root `/mnt/hdd/utopia/inspo/pi-ecosystem/pi-upstream` via live symlink), branch `main@4af9d21d3b4d664e4a29fcabfec85171077248e3`, 18,463 nodes / 81,629 edges, full mode; parse-partial caveats limited to docs/CSS/test fixtures (none cited here). Pass 2 (2026-08-24, legacy-sweep lane) re-pinned from `main@534bcbff` (+129 upstream commits): freshness verified by resolving drift-introduced `overrideConfig`. Pass 3 (2026-08-24, legacy-sweep lane) re-pinned from `main@a470b121` (+1 commit 4af9d21d "update managed installations in place"): the `pi-upstream` graph project had silently vanished from the CBM registry between passes — re-registered by path (`index_repository --repo-path <live-symlink-root> --name pi-upstream`) and content-freshness proven by resolving drift-introduced `runManagedSelfUpdate` :171–221 rank#1 before any citation; drift seam mined into managed-install-classification, staged-managed-self-update. Source and tests remain authoritative; the graph is a discovery index. Pass 4 (2026-08-26, miner-pi-upstream lane) deep pass on the uncited `packages/session-backends/sqlite-node` subsystem at the same pin: HEAD re-verified byte-for-byte against checkout; coverage checked on all 16 cited paths (15 `no_recorded_issue`; `001_initial.sql` parse-partial read directly before citing); work record created at `inspo/pi-upstream-work/` and the stale pass-0 ledger row reconciled to the leaf's real history.

## Boundaries
Adopt loop/compaction/session contracts and TUI input-reliability seams. Adapt provider transports, prompt wording, and timing windows to your host. Omit pi's package scaffolding (`packages/coding-agent`, `packages/client`, `packages/server`, extension examples), the AI-provider SDK surface (`packages/ai`), evals/telemetry plumbing, and TUI styling unless a target requires them. Pass-2 additions keep those boundaries: session persistence internals and the record-log reducer were promoted from omitted to mined because durable-session porting is a recurring question; `agent-harness.ts` orchestration and `env/nodejs.ts` remain omitted (thin composition over the seams mined here). Pass-3 exception: `package-manager-cli.ts` self-update internals were mined on a named drift seam (installer-managed in-place updates) despite living under the omitted scaffolding path; release-infra (`scripts/publish-release-announcement.mjs`, installer artifact publishing) stays omitted. Pass-4 exception: `packages/session-backends` was promoted from unlisted to mined because durable-session porting is a recurring porting question and the SQLite backend is the transactional twin of the mined JSONL record-log plane; the server/client RPC surface, `packages/ai`, extension examples, and export-html remain omitted.
