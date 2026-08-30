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
- **Alias canonicalizer safety rails** — `alias-canonicalizer-rails`: how do you rewrite names in text without corrupting unrelated prose.
- **Auto-dispatch probe** — `auto-dispatch-probe`: how do you choose batch vs sequential without losing the first item or misreading a blip.
- **Batch submitter rollover ladder** — `batch-rollover-ladder`: what happens when batch.create fails at page 40 of 50.
- **Boundary-aware splitting ladder** — `boundary-splitting-ladder`: how does every data type get split without corrupting its shape.
- **Chunk metadata marker courtesy** — `chunk-marker-courtesy`: how does an internal diagnostic marker coexist with caller domain data.
- **Contextualizer untrusted-content hardening** — `contextualizer-hardening`: how do you situate a chunk with an LLM when the chunk may be hostile.
- **Email & text loader timestamp fidelity** — `email-text-timestamp-fidelity`: how do Date headers and mtimes become created_at without lies.
- **Episode validation contract** — `episode-validation-contract`: what makes a record submittable, and why validation happens at construction.
- **JSON records loader identity mapping** — `json-records-identity-mapping`: how do structured records become unified-entity json episodes.
- **LimitGuard always-on safety net** — `limit-guard-safety-net`: how does an oversized episode NEVER reach the API.
- **LLM client adapters** — `llm-client-adapters`: how do optional provider SDKs plug into a complete(prompt) -> str protocol.
- **Ontology prompt-as-schema** — `ontology-prompt-schema`: how do Pydantic classes steer extraction classification.
- **Pipeline warning lifecycle** — `pipeline-warning-lifecycle`: how do warnings from reused components get collected without duplicates or loss.
- **Structural protocol extension surface** — `protocol-extension-surface`: how do you add a source, transform, submitter, or LLM without base classes.
- **IngestResult resume handles** — `result-resume-handles`: how does a caller recover an async bulk import from another process.
- **Retry safety taxonomy** — `retry-safety-taxonomy`: which failures may be retried, and what makes a retry safe.
- **Row-file schema gate** — `row-schema-gate`: how do JSONL/JSON inputs get validated against a dataclass without drift.
- **search_when_ready & error taxonomy** — `search-readiness-errors`: how do callers absorb indexing lag and classify failures.
- **Slack export inventory & selection** — `slack-inventory-selection`: how are four conversation indexes, wrapper folders, and path traversal handled.
- **Slack roster resolution** — `slack-roster-resolution`: how do you turn opaque user IDs into mergeable entity names.
- **Slack thread grouping & episode shaping** — `slack-thread-grouping`: what is the semantic unit, and how do timestamps and duplicates behave.
- **Thread backfill ownership** — `thread-backfill-ownership`: how do chat histories land on the right user's graph without cross-user writes.
- **Transcript turn parser** — `transcript-turn-parser`: how do you read speaker turns, WebVTT cues, and header blocks without misclassifying lines.
- **Fact triples & node seeding** — `triples-nodes-seeding`: how do you assert known facts and canonical entities deterministically.
- **Validated-replay spool** — `validated-replay-spool`: how does a lazy stream get fully validated before an async submitter consumes it.
- **Client-side validation helpers** — `validation-helpers`: how do shared field guards produce named errors instead of TypeErrors.
## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval against project `ext-zep`.

## Provenance
zep (getzep/zep), Apache-2.0, main @ `7de18dfa14da532cb782a0a14ae329e9a28b23d9`; Codebase Memory project `ext-zep` (12,820 nodes / 45,419 edges, FULL mode @ same HEAD = base_sha, zero drift; parse_partial x3 confined to example assets/css/env — none cited). Pass 1 mined `ingestion/src/zep_ingest` (~6,900 LOC) + `ontology/default_ontology.py` whole-file.

## Full view (memory graph)
Graph `ext-zep` resolves every cited seam line-exact via `search_graph --project ext-zep --query <symbol>`. TESTS edges (2,784) link each capsule to its direct test module (`ingestion/tests/test_*.py`). SIMILAR_TO/SEMANTICALLY_RELATED edges cluster the loader family (slack/email/text/transcript/json_records) and submitter family (batch/sequential).

## Boundaries
Adopt the validation-eagerly/stream-lazily/submission-recoverably architecture, the retry idempotency gate, and the omit-with-warning metadata etiquette as portable contracts. Adapt limit constants, status vocabularies, role sets, file formats, and warning copy to your host API. Omit Zep Cloud SDK types (BatchAddItem, BatchSummary, task-param recovery specifics), the MCP server and legacy Go planes, and benchmark harnesses — none are part of the ingestion contract mined here.
