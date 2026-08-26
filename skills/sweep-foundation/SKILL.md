---
name: sweep-foundation
description: "Use when porting GitHub-app webhook routers that fan out to long-running agent jobs: HMAC signature gates that must never fail closed-by-default, latest-wins thread replacement with ctypes async cancellation, per-object coalescing work queues, event/action gate ladders with bot-comment button toggles, GHA-autofix attribution chains, single-progress-comment UI lifecycles, and branch/commit/PR assembly with collision-retry naming. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# sweep: GitHub webhook dispatch & ticket lifecycle foundation

## Use this for
Use when porting GitHub-app webhook routers that fan out to long-running agent jobs: HMAC signature gates that must never fail closed-by-default, latest-wins thread replacement with ctypes async cancellation, per-object coalescing work queues, event/action gate ladders with bot-comment button toggles, GHA-autofix attribution chains, single-progress-comment UI lifecycles, and branch/commit/PR assembly with collision-retry naming. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/webhook-entry-signature-always-200.md` — what does a GitHub webhook endpoint owe GitHub: signature fail-open posture and swallow-all 200 responses?
- `references/latest-wins-ticket-thread-replacement.md` — how do you cancel a previous in-flight ticket job when a new event for the same issue arrives?
- `references/per-pr-comment-coalescing-queue.md` — how are rapid-fire PR comments serialized per object without unbounded worker growth?
- `references/event-router-gate-ladder.md` — which gate predicates route an event, and where does operator precedence let a restart button bypass them all?
- `references/gha-autofix-attribution-chain.md` — who is accountable for a bot-authored failing PR, and when may autofix fire?
- `references/single-progress-comment-lifecycle.md` — how does one mutable comment carry multi-step progress across token expiry?
- `references/branch-commit-pr-assembly-ladder.md` — how does a planned change-set become a named branch, commit, and PR without collisions?
- `references/chat-logger-ticket-ledger.md` — how do you count per-user ticket usage so quota gates and purchased-ticket spending stay consistent?
- `references/faster-model-tier-gate.md` — where does quota enforcement degrade a user to a cheap model vs hard-refuse the run?
- `references/snippet-type-taxonomy-funnel.md` — how do path-pattern tables route retrieved files into per-type budgets without a classifier?
- `references/digit-penalty-score-adjustment.md` — how do you demote generated/versioned/test-numbered files without a blocklist?
- `references/hybrid-search-multi-query-fusion.md` — how do lexical and vector scores combine, and how do multiple queries fold into one ranking?
- `references/pointwise-rerank-type-parallel.md` — how do you run an external reranker per category with frozen top ranks and a parallel/sequential fallback?
- `references/streamable-function-duality.md` — how does one pipeline function serve both a plain call site and a live progress UI?
- `references/llm-plan-continuation-and-repair.md` — how do truncated LLM plans get stitched across calls, and how are invalid change-requests patched by index?

## Capsule map
- **Webhook entry contract** — `webhook-entry-signature-always-200`: constant-time HMAC verify that fails OPEN without a secret; handler exceptions logged and swallowed so GitHub always gets 200.
- **Latest-wins threads** — `latest-wins-ticket-thread-replacement`: `repo-issue` keyed registry; old thread killed via `PyThreadState_SetAsyncExc(SystemExit)` with res==0/res!=1 cleanup ladder.
- **Coalescing priority queue** — `per-pr-comment-coalescing-queue`: lock-held put rebuilds heap keeping only `priority <= new`; named-worker guard via `threading.enumerate()`; blocking `get()` holds the same lock `put()` needs.
- **Event-router gate ladder** — `event-router-gate-ladder`: `match event, action`; label auto-provision tolerates 422 already_exists; `(gates) or restart_sweep` precedence bypass; buttons only count when `changes.body_from` present.
- **GHA autofix attribution** — `gha-autofix-attribution-chain`: sender→commit.author→assignee→refuse chain; base-passing precondition; <2 prior fix comments; free-tier refusal.
- **Progress-comment lifecycle** — `single-progress-comment-lifecycle`: reuse-first bot comment; `.edit` monkey-patched to append BOT_SUFFIX; BadCredentials recovery re-finds/recreates the comment.
- **Branch/commit/PR ladder** — `branch-commit-pr-assembly-ladder`: `/`→`_` swap if bare `sweep` branch exists; 9× `_hash5` suffix retries; 50-char commit message; polluted-path sanitization; draft conversion last.
- **Ticket ledger write path** — `chat-logger-ticket-ledger`: month+date `$inc` upsert counters keyed on username; same-pass `purchased_tickets: -1` when over cap; gpt3 tickets isolated in `{month}_gpt3`; class-level read caches; off-thread writes parked in `global_threads`.
- **Faster-model tier gate** — `faster-model-tier-gate`: use_faster_model ladder (payer ≥500, trial ≥20, free ≥5-monthly/>3-daily, inactive ⇒ always); Mongo-down degrades fail-closed; determine_model raises ValueError inside call_openai when allocation exhausted with purchased==0.
- **Snippet type taxonomy** — `snippet-type-taxonomy-funnel`: first-match prefix/suffix/substring tables → tools/junk/deps/docs/tests/source; four per-type tuning dicts (percentile floor, score floor, result count, rerank budget); junk excluded structurally by __iter__ never yielding it (the "junk" override guard is dead code).
- **Digit-penalty scoring** — `digit-penalty-score-adjustment`: `(1 − 1/len(basename))^digits` multiplicative decay applied at BOTH hybrid fusion and rerank ingestion; empty basename ⇒ literal 0.
- **Hybrid multi-query fusion** — `hybrid-search-multi-query-fusion`: `(lex + 2·vector)/3` with 0.04/0.02 floors for one-sided matches; k·3 over-fetch then position-decayed `1/2^j` fold privileging query #0.
- **Pointwise per-type rerank** — `pointwise-rerank-type-parallel`: no keys ⇒ identity; scores squashed ÷10¹² baseline; top-5 frozen ×1000 AFTER reranker writes; Cohere→Voyage key ladder; ThreadPoolExecutor per type with identical sequential fallback; percentile+score-floor cutoffs and empty→source fallback.
- **Streamable duality** — `streamable-function-duality`: plain call drains yields and returns StopIteration.value else last yield; `.stream()` exposes raw generator for UI consumers; returns are authoritative, yields advisory snapshots.
- **Plan continuation & repair** — `llm-plan-continuation-and-repair`: stop-token-bounded concatenating continuation (≤10 calls, tail-truncated resume prompt, cleanup-mutated history, swallowed continuation failures); ≤3-round index-addressed FCR repair with descending-order drops and filename-only COPIED_FROM_PREVIOUS_MODIFY overrides.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
sweepai/sweep (Apache-2.0), `main@a8b8b67bda4f89faac9314d34e7c7d5a64f76046` (pin UNCHANGED through pass 2); Codebase Memory project `sweep` (full mode, gen 2026-08-25T20:08:36Z, 4788n/16471e; parse-partial limited to redis.conf + binary .pkl fixtures, none cited). Pass 1 (7 capsules): webhook dispatch → ticket lifecycle. Pass 2 (+8 capsule-v2, 15 total): ticket context pipeline — ChatLogger quota ledger, faster-model tier gate, snippet type taxonomy, digit-penalty scoring, hybrid multi-query fusion, pointwise per-type rerank, streamable function duality, LLM plan continuation & FCR repair. Coverage: check_index_coverage no_recorded_issue ×6 cited paths; no offline unit tests exist for the pass-2 modules (per-capsule caveats).

## Full view (memory graph)
Revalidate `sweep` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Executed at pin: pass 1 ran `python3 -m unittest sweepai.utils.buttons_test -v` → 7 OK offline; `tests/e2e/*` and `tests/test_gha_extraction.py` need `GITHUB_PAT`/live API — standing runner block. Pass 2 graph TESTS-edge query over its five modules returned zero rows both directions (no direct tests exist); deterministic grep probes + live retrieves substituted.

## Boundaries
Adopt the pure contracts (signature ladder, thread-key cancellation, coalescing put semantics, gate-ladder structure, attribution fallback order, branch-name retry ladder); adapt the transport specifics (FastAPI dependency wiring, PyGithub client calls, loguru contextualize) to your host; omit Sweep's product behavior (license validation, PostHog/Sentry telemetry, free-tier gating messages, Discord suffixes).
