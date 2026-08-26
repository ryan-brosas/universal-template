---
name: zep-foundation
description: "Use when porting Zep's bulk graph-ingestion engine: streaming pipelines, batch/sequential submission, retry safety, entity canonicalization, or memory-backfill validation."
disable-model-invocation: true
---

# Zep (getzep/zep): Graph Memory Ingestion Foundation

## Use this for
Porting any system that loads unstructured and structured data into a knowledge/memory graph correctly: source loaders (Slack exports, transcripts, email, text corpora, JSON records), lazy transform pipelines (chunking, LLM contextualization, alias canonicalization), always-on limit enforcement, rate-limit-aware submission over Batch and sequential paths with honest fallbacks, resume-handle result objects for asynchronous imports, client-side schema gates that produce named errors instead of HTTP 400s mid-run. The zep_ingest package is the reference implementation of "validate eagerly at construction, submit asynchronously, never lose already-submitted work." Source and direct tests are ground truth.

## Load the matching source dump
- `references/episode-validation-contract.md` — what makes a record submittable before any API call?
- `references/protocol-extension-surface.md` — how do Loaders/Transforms/Submitters/LLM clients plug in without base classes?
- `references/pipeline-warning-lifecycle.md` — collecting per-component warnings across preview+run on reused objects?
- `references/validated-replay-spool.md` — full validation of a lazy stream before async consumption?
- `references/retry-safety-taxonomy.md` — which failures may be retried, and what makes a retry safe?
- `references/batch-rollover-ladder.md` — surviving batch.create failure at page 40 of 50?
- `references/auto-dispatch-probe.md` — choosing batch vs sequential without losing the peeked item?
- `references/result-resume-handles.md` — recovering an async import from another process?
- `references/boundary-splitting-ladder.md` — splitting text/message/json without corrupting shape?
- `references/limit-guard-safety-net.md` — the invisible 10k-char episode ceiling?
- `references/alias-canonicalizer-rails.md` — rewriting entity names without corrupting prose?
- `references/chunk-marker-courtesy.md` — internal diagnostic metadata vs caller domain data?
- `references/contextualizer-hardening.md` — LLM chunk-contextualization under untrusted content?
- `references/slack-roster-resolution.md` — opaque user IDs to mergeable entity names?
- `references/slack-inventory-selection.md` — four conversation indexes, wrapper folders, traversal defense?
- `references/slack-thread-grouping.md` — threads as episodes: ordering, dedupe, timestamp stamping?
- `references/transcript-turn-parser.md` — speaker turns, VTT cues, header disambiguation?
- `references/email-text-timestamp-fidelity.md` — Date headers and mtimes as honest created_at?
- `references/json-records-identity-mapping.md` — unified-entity field lifting with provenance reserved?
- `references/thread-backfill-ownership.md` — chat-history backfill without cross-user writes?
- `references/triples-nodes-seeding.md` — asserting known facts and canonical nodes deterministically?
- `references/validation-helpers.md` — shared field guards and the two finiteness regimes?
- `references/row-schema-gate.md` — dataclass-derived JSONL row validation?
- `references/search-readiness-errors.md` — indexing-lag polling and the error taxonomy?
- `references/ontology-prompt-schema.md` — Pydantic docstrings as extraction instructions?
- `references/llm-client-adapters.md` — complete(prompt)->str adapters for any provider?

## Capsule map
- `episode-validation-contract` — eager collect-all-errors Episode/Destination validation; internal fields never sent.
- `protocol-extension-surface` — runtime_checkable structural protocols; optional warnings/flush capabilities.
- `pipeline-warning-lifecycle` — id-keyed baseline deltas make components reusable across preview+run passes.
- `validated-replay-spool` — spooled pickle validates the whole lazy stream before async submission.
- `retry-safety-taxonomy` — 429/unsent-transport retryable; 5xx only behind caller-established idempotency; Retry-After capped.
- `batch-rollover-ladder` — first-create raises (fallback possible), rollover records-and-stops keeping batch ids; 404-only availability signal.
- `auto-dispatch-probe` — real-call availability probe + chain-back-the-peeked-item.
- `result-resume-handles` — from_batch_ids/from_task_ids reconstruction; gap-slotted parallel identity lists; untracked ≠ failed.
- `boundary-splitting-ladder` — paragraph→sentence→hard ladder; JSON pieces stay valid JSON or return None.
- `limit-guard-safety-net` — post-transform per-type guard; never yield the oversize original.
- `alias-canonicalizer-rails` — risky-word gate, protected spans, lookaround boundaries, per-alias counts.
- `chunk-marker-courtesy` — omit-with-warning internal metadata markers; caller domain data always wins.
- `contextualizer-hardening` — symmetric tag-stripping, data-not-instructions prompt, fail-open default.
- `slack-roster-resolution` — real_name-first for entity merging; deferred weak-name promotion.
- `slack-inventory-selection` — marker-based export-root unwrap, dual readers, loud skip accounting, traversal defense.
- `slack-thread-grouping` — thread-as-unit episodes, original-timestamp stamping, counted duplicate/ts defenses.
- `transcript-turn-parser` — asymmetric-cost header matching, position-strict VTT identifiers, offset timestamps.
- `email-text-timestamp-fidelity` — -0000 preserved as UTC; mtime opt-in warned.
- `json-records-identity-mapping` — original-record field reads, reserved provenance keys, path-naming NaN rejection.
- `thread-backfill-ownership` — user-must-exist, global-thread-id ownership verification, sentence-boundary splits.
- `triples-nodes-seeding` — SCREAMING_SNAKE facts, UUID endpoint pinning, None-gap identity alignment.
- `validation-helpers` — check_*/require_* split; JSON-shape vs C-clock finiteness regimes.
- `row-schema-gate` — dataclass-derived allowed/required sets, retired-field migration messages.
- `search-readiness-errors` — poll-until-indexed helper; untracked-as-unknown; partial_result-carrying exceptions.
- `ontology-prompt-schema` — priority-ordered docstring guidance inside Pydantic schemas.
- `llm-client-adapters` — one-method protocol, injectable duck-typed clients, type-based response extraction.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval against project `ext-zep`.

## Provenance
zep (getzep/zep), Apache-2.0, main @ `7de18dfa14da532cb782a0a14ae329e9a28b23d9`; Codebase Memory project `ext-zep` (12,820 nodes / 45,419 edges, FULL mode @ same HEAD = base_sha, zero drift; parse_partial x3 confined to example assets/css/env — none cited). Pass 1 mined `ingestion/src/zep_ingest` (~6,900 LOC) + `ontology/default_ontology.py` whole-file.

## Full view (memory graph)
Graph `ext-zep` resolves every cited seam line-exact via `search_graph --project ext-zep --query <symbol>`. TESTS edges (2,784) link each capsule to its direct test module (`ingestion/tests/test_*.py`). SIMILAR_TO/SEMANTICALLY_RELATED edges cluster the loader family (slack/email/text/transcript/json_records) and submitter family (batch/sequential).

## Boundaries
Adopt the validation-eagerly/stream-lazily/submission-recoverably architecture, the retry idempotency gate, and the omit-with-warning metadata etiquette as portable contracts. Adapt limit constants, status vocabularies, role sets, file formats, and warning copy to your host API. Omit Zep Cloud SDK types (BatchAddItem, BatchSummary, task-param recovery specifics), the MCP server and legacy Go planes, and benchmark harnesses — none are part of the ingestion contract mined here.
