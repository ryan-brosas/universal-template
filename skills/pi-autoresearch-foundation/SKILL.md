---
name: pi-autoresearch-foundation
description: "Use when porting an autonomous run→measure→keep/discard optimization loop for an LLM agent — JSONL-as-source-of-truth persistence, MAD noise-floor confidence scoring, git-worktree isolation with keep-commits/revert-discards, benchmark-script run-locking, backpressure checks, deterministic compaction summaries, self-resume gates, or file-backed live dashboards. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

---
# pi-autoresearch-harness: autonomous experiment-loop foundation

## Use this for
Use when porting an autonomous run→measure→keep/discard optimization loop for an LLM agent — JSONL-as-source-of-truth persistence, MAD noise-floor confidence scoring, git-worktree isolation with keep-commits/revert-discards, benchmark-script run-locking, backpressure checks, deterministic compaction summaries, self-resume gates, or file-backed live dashboards. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/jsonl-append-only-source-of-truth.md` — which writes create vs extend the ledger, and why manual edits are legal?
- `references/mad-confidence-scoring.md` — how is improvement-vs-noise computed, and when is confidence deliberately null?
- `references/baseline-vs-best-metric-trap.md` — why does `state.bestMetric` hold the BASELINE, and where is the real best derived?
- `references/segment-reinit-protocol.md` — how does re-init archive history via monotone segments without deleting anything?
- `references/secondary-metric-registry.md` — how do optional metrics become exact-set schema with an explicit-force growth path?
- `references/target-max-stop-conditions.md` — how does the loop end itself through both a machine flag and imperative text?
- `references/metric-line-grammar.md` — what is the `METRIC name=value` grammar, denylist, and duplicate rule?
- `references/autoresearch-sh-run-lock.md` — how is arbitrary-command escape blocked once a benchmark script exists?
- `references/backpressure-checks-gate.md` — how do correctness checks veto keeps while staying out of the measured metric?
- `references/dual-plane-output-truncation.md` — why does the LLM see 10 tail lines while full output spills to a temp file?
- `references/detached-process-group-timeout.md` — what spawn flags make whole-tree kill work, and why does timedOut override exit 0?
- `references/worktree-auto-detect-create.md` — how is the right isolated checkout found after restart, and what makes creation idempotent?
- `references/keep-commit-revert-protected-files.md` — what happens to the tree on keep vs discard, and which five files survive reverts?
- `references/session-scoped-runtime-store.md` — what cache key isolates concurrent sessions sharing one server?
- `references/settled-gate-auto-resume.md` — when does the loop nudge itself onward, and what stops it forever at 20 turns?
- `references/deterministic-compaction-summary.md` — why skip the LLM at compaction and rebuild context from disk instead?
- `references/jsonl-file-watcher.md` — how does cross-process UI truth ride a 500ms poll with a single handle?
- `references/iteration-hooks-steer-channel.md` — how can external scripts advise the loop without ever blocking it?
- `references/system-prompt-mode-injection.md` — which instructions re-inject per turn, adapting to which session files exist?
- `references/cli-server-lifecycle.md` — how does a per-command CLI get a persistent backend, and why wait an hour for one action?
- `references/widget-state-machine.md` — what widget precedence hides transient states, and which width invariant prevents TUI crashes?
- `references/adaptive-table-column-budget.md` — how do N metric columns share one line with an ellipsis reserve and 25% description floor?
- `references/stratified-scatter-sampling.md` — which runs get plotted beyond 30 points, and why median-of-bucket representatives?
- `references/fullscreen-scroll-overlay.md` — what is the custom-TUI contract for scrolling, spinner animation, and clean disposal?
- `references/live-sse-dashboard-export.md` — how does a static HTML page become a live JSONL view over a two-path allowlist?
- `references/shortcut-config-resolution.md` — what tri-state grammar lets users override or disable keybindings safely?
- `references/skill-extension-separation.md` — where does domain knowledge end and loop infrastructure begin?
- `references/asi-free-form-diagnostics.md` — how does per-run reasoning get captured schema-free yet surface three promoted keys?

## Capsule map
- **Persistence kernel** — `jsonl-append-only-source-of-truth`: write-once config header + append-only runs; replay skips malformed lines; no second source of truth may exist. · `jsonl-file-watcher`: fs.watchFile(500ms) whole-file reconstruction preserves only worktreeDir; idempotent start, close-then-null teardown. · `session-scoped-runtime-store`: sessions keyed `cwd:sessionId`; reset preserves exactly one field.
- **Statistics** — `mad-confidence-scoring`: |bestKept − firstValid| / MAD(all valid), five null gates, advisory-only. · `baseline-vs-best-metric-trap`: bestMetric stores the SEGMENT BASELINE; findBestMetric derives the true optimum on demand; deltas divide by baseline.
- **Loop lifecycle** — `segment-reinit-protocol`: re-init bumps currentSegment + nulls baseline/confidence but appends, never truncates; UI filters per segment while confidence pools globally. · `secondary-metric-registry`: first-seen registration with inferred units; logs must match the known set exactly; new keys need --force. · `target-max-stop-conditions`: max-experiments pre-blocks run; target fires only on kept positive crossings; both flip mode off AND command STOP text.
- **Benchmark execution** — `metric-line-grammar`: anchored `^METRIC ([\w.µ]+)=(\S+)$`, prototype-name denylist, Number.isFinite gate, last-wins Map. · `autoresearch-sh-run-lock`: strip env/wrapper prefixes to fixpoint then anchor-match autoresearch.sh as FIRST command; rejects chains and look-alikes. · `backpressure-checks-gate`: checks run post-benchmark on their own timeout; pass=null/true/false tri-state; failed checks make keep server-side impossible. · `dual-plane-output-truncation`: LLM gets last 10 lines / 4KB; >50KB streams spill whole to temp; METRIC parsing always sees untruncated output. · `detached-process-group-timeout`: spawn detached ⇒ kill(-pid) hits the group; taskkill /t on Windows; killed=true forces failure regardless of exit code.
- **Git isolation** — `worktree-auto-detect-create`: porcelain walk canonicalizes paths, requires `autoresearch/<id>` suffix AND existing jsonl marker; create prunes stale entries, branch-per-session, global-gitignore self-seeding. · `keep-commit-revert-protected-files`: keep = add -A + Result:-JSON commit + sha restamp; non-keep = stage the five session files BEFORE checkout--. + clean -fd so the loop's memory survives any revert.
- **Agent-loop control** — `settled-gate-auto-resume`: strict turn gate (ran ≥1 experiment) vs permissive compaction gate; 800ms settle window; hard cap 20 auto-resumes. · `deterministic-compaction-summary`: six synthesized sections replace LLM summarization; last-50 window still computes deltas against the true segment baseline. · `system-prompt-mode-injection`: per-turn conditional append; rules-path, ideas-backlog, checks-doctrine blocks keyed on file existence; shared anti-overfit guardrail constant. · `cli-server-lifecycle`: lazy detached daemon + 15s readiness poll; action POSTs block up to 1h because run must return benchmark results synchronously.
- **Extensibility surfaces** — `iteration-hooks-steer-channel`: executable-only before/after.sh get JSON on stdin; stdout becomes advice text capped UTF-8-safe at 8KB; logging gated on config-header presence. · `shortcut-config-resolution`: undefined⇒default, string⇒override, null⇒disabled; hints derive from the same resolution as registrations. · `skill-extension-separation`: code owns state/git/statistics; prose owns goal-interpretation and authors autoresearch.sh emitting METRIC lines; one extension serves unlimited domains. · `asi-free-form-diagnostics`: `[key: string]: unknown` accepted verbatim, empty dicts stripped; compaction promotes exactly hypothesis/next_action_hint/rollback_reason.
- **Observability** — `widget-state-machine`: results-dashboard > ready > hidden precedence; width=termWidth−2 padding compensation prevents wrap-crash; confidence color ladder triplicated across renderers. · `adaptive-table-column-budget`: essentials full width; secondaries admitted by prefix fit-scan reserving ellipsis + max(25,25%) description floor. · `stratified-scatter-sampling`: first + ≤19 median-of-bucket + last-10 points; x-labels reconstruct original run numbers; meaningful symbols overwrite '·' never reverse. · `fullscreen-scroll-overlay`: ui.custom overlay contract render/handleInput/dispose; spinner interval animates only while running and MUST be cleared on close. · `live-sse-dashboard-export`: two-path serve allowlist (`/`, `/autoresearch.jsonl`) + `/events` SSE; same-workdir reuse swaps HTML pointer keeping clients connected.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-autoresearch-harness (MIT), `main@511760df8905c7b6e6bbd3a028de734becff69e6` (= base_sha, zero drift, v1.0.5 release commit); Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness` (658n/1508e FULL ready, parse_partial ×0, exclusions = 3 image suffixes). Pass 1 (2026-08-24) mined all 41 production TS files whole-file (~9.3k LOC incl. harness server 1711L + extension entry 1148L).

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph verified ready at head==base==pin with zero parse_partial. Note: small graph (658 nodes) — search_graph resolves symbols line-exact; for prose/doc seams fall back to `search_code --pattern`. Direct tests: 82 unit assertions across 11 suites (utils/state/runtime-store/compaction/jsonl/git/shortcuts/platform/tools/regression/fullscreen-width) + 17 integration (worktree/session-isolation); vitest runner NOT installed in the inspo clone (no node_modules) — probes executed as deterministic grep anchors from repo root, expectations re-derived against live source pre-write.

## Boundaries
Adopt pure contracts: JSONL protocol, MAD formula, segment arithmetic, run-lock predicate, protected-file ordering, stop ladders, tri-state shortcut grammar. Adapt host-specific integration: pi ExtensionAPI events (before_agent_start/session_before_compact/ui.custom), pi-tui rendering, HTTP transport/port env names, Windows bash resolution. Omit product-specific behavior: npm publish packaging, GitHub Actions CI, logo/template assets, the davebcn87 upstream fork lineage details.
