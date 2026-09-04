<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Mike (MikeOSS): Legal-AI Chat & Document Foundation

## Use this for
Porting any assistant backend that lets an LLM read/write user documents safely: per-request nonce-fenced spotlighting of every user-controlled string (filenames, document bodies, profile facts), a three-tier tolerant quote verifier that swaps drifted quotes back to exact source text, non-expiring HMAC-signed download links safe to store in chat history, an owner-or-shared-email access ladder that replaced scope-by-user_id when sharing landed, fire-and-forget audit mining from assistant event streams, upload-before-insert replication with compensating deletes, turn-scoped read/edit dedup maps keyed by document:version identity, and a reserved-row + null-content-skip SSE persistence protocol. Express + Supabase/Postgres + S3-compatible storage; patterns port to any stack. Source and direct tests are ground truth.

## Load the matching source dump
- `./download-token-signing.md` — persistent file links without signed-URL expiry?
- `./shared-access-ladder.md` — who may read a doc under project sharing?
- `./audit-turn-mining.md` — one chat row plus artifact rows, never throwing?
- `./ssrf-ip-classifier.md` — which IP literals are fail-closed blocked?
- `./citation-tolerant-normalizer.md` — surviving LLM-shaped citation JSON?
- `./citations-diagnostics-triple-state.md` — no-block vs broken-block vs parsed?
- `./streaming-partial-citations.md` — citation cards while tokens still stream?
- `./spotlight-nonce-fence.md` — untrusted text that cannot forge its way out?
- `./workflow-fence-semi-trusted.md` — instructions to follow vs data to read?
- `./prior-turn-event-recap.md` — what did my last turn produce, injection-free?
- `./doc-context-sweeps.md` — which docs exist across the whole chat history?
- `./workflow-store-overlay.md` — catalog under user workflows without crashing?
- `./route-stream-reservation.md` — crash-safe SSE persistence rows?
- `./stream-citations-gate.md` — hiding the CITATIONS block from visible deltas?
- `./sse-error-sanitizer.md` — internal errors never reach the browser?
- `./model-allowlist-choke-point.md` — router models the user never saved?
- `./tool-dispatch-contract.md` — one result per tool_use, always?
- `./replicate-upload-first.md` — N copies with zero half-created rows?
- `./immutable-source-guard.md` — templates edited only through copies?
- `./turn-read-edit-lifecycle.md` — read-once-per-turn without stale bytes?
- `./quote-verification-ladder.md` — proving or correcting model quotes against source?
- `./auth-mfa-assurance-ladder.md` — step-up verification with asymmetric fail-open/closed?
- `./courtlistener-turn-cache.md` — turn-scoped case cache with gated opinion reads?
- `./ask-input-normalization.md` — clamped user-input pickers that pause the turn?
- `./read-pipeline-extraction-ladder.md` — one reader for PDF/DOCX/XLSX/PPTX?

## Capsule map
- **Ask inputs normalization** — `ask-input-normalization`: how does a user-input picker tool survive malformed model arguments and pause the turn.
- **Audit turn mining** — `audit-turn-mining`: how do you record one chat row plus its artifact rows without ever breaking the chat.
- **Auth MFA assurance ladder** — `auth-mfa-assurance-ladder`: when must a valid bearer token still be rejected for step-up verification.
- **Citation tolerant normalizer** — `citation-tolerant-normalizer`: how do you survive LLM-shaped citation JSON without dropping valid entries.
- **Citations diagnostics triple-state** — `citations-diagnostics-triple-state`: was the CITATIONS block absent, broken, or empty.
- **CourtListener turn cache** — `courtlistener-turn-cache`: how does opinion text get cached per turn so find/read/verify never re-fetch.
- **Doc context sweeps** — `doc-context-sweeps`: which documents exist for this chat, including ones never attached to a user message.
- **Download token signing** — `download-token-signing`: how do persistent file links survive without signed-URL expiry.
- **Immutable source guard** — `immutable-source-guard`: how do library templates get protected from in-place edits while staying readable.
- **Model allowlist choke point** — `model-allowlist-choke-point`: how do router-prefixed model ids get validated exactly once per request.
- **Prior-turn event recap** — `prior-turn-event-recap`: how does the model learn what its last turn produced without re-reading raw events.
- **Quote verification ladder** — `quote-verification-ladder`: how does the server prove (or correct) a model quote against real document text.
- **Read pipeline extraction ladder** — `read-pipeline-extraction-ladder`: how does one reader serve PDF/DOCX/XLSX/PPTX and mislabeled legacy files.
- **Replicate upload-first** — `replicate-upload-first`: how do you create N document copies with zero half-created rows.
- **Route stream reservation** — `route-stream-reservation`: how does SSE persistence survive crashes and concurrent streams.
- **Shared-project access ladder** — `shared-access-ladder`: who may read a document once projects can be shared.
- **Spotlight nonce fence** — `spotlight-nonce-fence`: how does untrusted user text get shown to an LLM without becoming instructions.
- **SSE error sanitizer** — `sse-error-sanitizer`: how do internal errors stream to a browser without leaking internals.
- **SSRF IP classifier** — `ssrf-ip-classifier`: which address literals must an outbound-fetch guard reject, fail-closed.
- **Stream citations gate** — `stream-citations-gate`: how do you hide the CITATIONS block from visible deltas while still streaming it to the parser.
- **Streaming partial citations** — `streaming-partial-citations`: how do citation cards appear while the JSON is still streaming.
- **Tool dispatch contract** — `tool-dispatch-contract`: how does every tool_use get exactly one tool_result even when a branch fails or is unknown.
- **Turn read/edit lifecycle** — `turn-read-edit-lifecycle`: how does read-once-per-turn dedup stay correct when edits change the bytes.
- **Workflow fence semi-trusted** — `workflow-fence-semi-trusted`: how do you let the model FOLLOW installed instructions without letting them override policy.
- **Workflow store overlay** — `workflow-store-overlay`: how do catalog workflows coexist with user workflows without crashing the chat.
## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source excerpt, invariant, byte-exact Probe against the repo checkout (`cd $REFERENCE_ROOT/external/mike/backend`), and `search_graph` Retrieve against project `ext-mike`. Keep the canonical pinned commit; never vendor modules.

## Provenance
mike (MikeOSS legal-AI platform), AGPL-3.0 — **patterns-only**: adopt behavior contracts, never copy code verbatim into non-AGPL hosts. main @ `3ad9a5ffafd6ad21624a7c11a23188d3dc674b7d`; Codebase Memory project `ext-mike` (7,357 nodes / 25,035 edges, FULL mode @ same HEAD = base_sha, zero drift; parse_partial x60 confined to SQL migrations/CSS/test fixtures — none cited). Pass 1 whole-file mined backend planes: lib/{access,audit,privateIp,downloadTokens}, chat/{citations,contextBuilders,routeStreaming,stream­ing,verifyCitations,types}, chat/tools/{toolDispatcher,documentOps,courtlistenerTurnState}, middleware/auth (~7,400 LOC).

## Full view (memory graph)
Graph `ext-mike` resolves every cited seam line-exact via `search_graph --project ext-mike --query <symbol>` (BM25 over Function/Type nodes; Route nodes carry HTTP surfaces). Direct suites live beside their modules (`src/lib/__tests__/*.test.ts`, `src/lib/chat/*.test.ts`, `src/lib/chat/__tests__/`, `src/lib/chat/tools/*.test.ts`) and run with `bunx vitest run <file>` from `backend/`. SIMILAR_TO edges cluster the generate_* family (docx/xlsx/ppt) sharing `registerGeneratedDocument`.

## Boundaries
Adopt the fence-neutralize-verify pipeline (spotlight everything user-controlled; verify quotes server-side; swap drifted text), the upload-before-insert durability order with compensating deletes, and the reserved-row persistence protocol as portable contracts. Adapt limits (300-char audit titles, 200k context cap, 3-quote ceiling, 12-item ask_inputs), storage/table names, and event-type vocabulary to your host. Omit the Next.js frontend, Word add-in plane, e2e/loadtest harness, CourtListener provider internals beyond the turn-cache contract, and the MFA assurance ladder (queued pass-2 with courtlistenerTools) — none are part of the seams mined here.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`ask-input-normalization.md`](./ask-input-normalization.md)
- [`audit-turn-mining.md`](./audit-turn-mining.md)
- [`auth-mfa-assurance-ladder.md`](./auth-mfa-assurance-ladder.md)
- [`citation-tolerant-normalizer.md`](./citation-tolerant-normalizer.md)
- [`citations-diagnostics-triple-state.md`](./citations-diagnostics-triple-state.md)
- [`courtlistener-turn-cache.md`](./courtlistener-turn-cache.md)
- [`doc-context-sweeps.md`](./doc-context-sweeps.md)
- [`download-token-signing.md`](./download-token-signing.md)
- [`immutable-source-guard.md`](./immutable-source-guard.md)
- [`model-allowlist-choke-point.md`](./model-allowlist-choke-point.md)
- [`prior-turn-event-recap.md`](./prior-turn-event-recap.md)
- [`quote-verification-ladder.md`](./quote-verification-ladder.md)
- [`read-pipeline-extraction-ladder.md`](./read-pipeline-extraction-ladder.md)
- [`replicate-upload-first.md`](./replicate-upload-first.md)
- [`route-stream-reservation.md`](./route-stream-reservation.md)
- [`shared-access-ladder.md`](./shared-access-ladder.md)
- [`spotlight-nonce-fence.md`](./spotlight-nonce-fence.md)
- [`sse-error-sanitizer.md`](./sse-error-sanitizer.md)
- [`ssrf-ip-classifier.md`](./ssrf-ip-classifier.md)
- [`stream-citations-gate.md`](./stream-citations-gate.md)
- [`streaming-partial-citations.md`](./streaming-partial-citations.md)
- [`tool-dispatch-contract.md`](./tool-dispatch-contract.md)
- [`turn-read-edit-lifecycle.md`](./turn-read-edit-lifecycle.md)
- [`workflow-fence-semi-trusted.md`](./workflow-fence-semi-trusted.md)
- [`workflow-store-overlay.md`](./workflow-store-overlay.md)
