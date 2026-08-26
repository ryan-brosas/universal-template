---
name: mike-foundation
description: "Use when porting MikeOSS legal-AI platform contracts: nonce-fenced prompt-injection spotlighting, server-side quote verification, HMAC download tokens, shared-project access ladders, or SSE tool-stream choreography."
disable-model-invocation: true
---

# Mike (MikeOSS): Legal-AI Chat & Document Foundation

## Use this for
Porting any assistant backend that lets an LLM read/write user documents safely: per-request nonce-fenced spotlighting of every user-controlled string (filenames, document bodies, profile facts), a three-tier tolerant quote verifier that swaps drifted quotes back to exact source text, non-expiring HMAC-signed download links safe to store in chat history, an owner-or-shared-email access ladder that replaced scope-by-user_id when sharing landed, fire-and-forget audit mining from assistant event streams, upload-before-insert replication with compensating deletes, turn-scoped read/edit dedup maps keyed by document:version identity, and a reserved-row + null-content-skip SSE persistence protocol. Express + Supabase/Postgres + S3-compatible storage; patterns port to any stack. Source and direct tests are ground truth.

## Load the matching source dump
- `references/download-token-signing.md` — persistent file links without signed-URL expiry?
- `references/shared-access-ladder.md` — who may read a doc under project sharing?
- `references/audit-turn-mining.md` — one chat row plus artifact rows, never throwing?
- `references/ssrf-ip-classifier.md` — which IP literals are fail-closed blocked?
- `references/citation-tolerant-normalizer.md` — surviving LLM-shaped citation JSON?
- `references/citations-diagnostics-triple-state.md` — no-block vs broken-block vs parsed?
- `references/streaming-partial-citations.md` — citation cards while tokens still stream?
- `references/spotlight-nonce-fence.md` — untrusted text that cannot forge its way out?
- `references/workflow-fence-semi-trusted.md` — instructions to follow vs data to read?
- `references/prior-turn-event-recap.md` — what did my last turn produce, injection-free?
- `references/doc-context-sweeps.md` — which docs exist across the whole chat history?
- `references/workflow-store-overlay.md` — catalog under user workflows without crashing?
- `references/route-stream-reservation.md` — crash-safe SSE persistence rows?
- `references/stream-citations-gate.md` — hiding the CITATIONS block from visible deltas?
- `references/sse-error-sanitizer.md` — internal errors never reach the browser?
- `references/model-allowlist-choke-point.md` — router models the user never saved?
- `references/tool-dispatch-contract.md` — one result per tool_use, always?
- `references/replicate-upload-first.md` — N copies with zero half-created rows?
- `references/immutable-source-guard.md` — templates edited only through copies?
- `references/turn-read-edit-lifecycle.md` — read-once-per-turn without stale bytes?
- `references/quote-verification-ladder.md` — proving or correcting model quotes against source?
- `references/auth-mfa-assurance-ladder.md` — step-up verification with asymmetric fail-open/closed?
- `references/courtlistener-turn-cache.md` — turn-scoped case cache with gated opinion reads?
- `references/ask-input-normalization.md` — clamped user-input pickers that pause the turn?
- `references/read-pipeline-extraction-ladder.md` — one reader for PDF/DOCX/XLSX/PPTX?

## Capsule map
- `download-token-signing` — HMAC over base64url payload; verify BEFORE decode; timing-safe compare on encoded form.
- `shared-access-ladder` — owner → direct share list → project share; email compare lowercased; isOwner returned separately.
- `audit-turn-mining` — try/catch-swallowed inserts; title clamped 300; doc_replicated fans out per copy.
- `ssrf-ip-classifier` — BlockList ranges; IPv6 global-unicist gate 2000::/3; NAT64 re-classified by embedded v4.
- `citation-tolerant-normalizer` — ref-or-[N]-marker, quote/text alias, camelCase ids, ≤3 quotes, junk page→1.
- `citations-diagnostics-triple-state` — hasBlock/rawLength/error distinguates absent, malformed, and empty blocks.
- `streaming-partial-citations` — string-aware brace scanner emits complete objects mid-stream; count-monotonic snapshots.
- `spotlight-nonce-fence` — 32-hex nonce on BOTH tags; echoed nonce redacted; smuggled tags HTML-escaped.
- `workflow-fence-semi-trusted` — <workflow-instructions> follows but never overrides policy; same neutralization.
- `prior-turn-event-recap` — last assistant events replayed as tool-activity lines, filenames fenced.
- `doc-context-sweeps` — attachments ∪ prior doc_created/edited/replicated UUIDs; ready-only; stable doc-N slugs.
- `workflow-store-overlay` — catalog listed:false under user listed:true; best-effort defaults; reference files attached.
- `route-stream-reservation` — pre-insert null row skips crashes AND concurrent streams; 3-attempt updater.
- `stream-citations-gate` — tail buffer holds back tag-length−1 chars; post-marker deltas go to hidden parser only.
- `sse-error-sanitizer` — error events whitlisted via safe_to_display; per-event error strings replaced wholesale.
- `model-allowlist-choke-point` — single resolveRequestedModel(throw) inside try so blips become stream errors.
- `tool-dispatch-contract` — results keyed by tool_call_id; missing result synthesized so Claude gets N-of-N.
- `replicate-upload-first` — client UUIDs, parallel uploads, bulk inserts, compensating delete, failed_copies reported.
- `immutable-source-guard` — template/asset edits vetoed with UI-shaped failure; replicate requires new_filename.
- `turn-read-edit-lifecycle` — dedup key documentId:versionId; edit invalidates reads; label repointed to new version.
- `quote-verification-ladder` — 3-tier tolerant locate with index-map back-mapping; drift swapped to exact excerpt; fabricated preserved-but-unverified.
- `auth-mfa-assurance-ladder` — aal2 step-up gate; missing-column read fails open, assurance lookup fails closed; bootstrap route carve-out.
- `courtlistener-turn-cache` — first-field-wins upsert, refreshable non-empty opinions; text server-side only; multi-opinion reads demand explicit ids.
- `ask-input-normalization` — clamp-with-default picker items; persist-then-pause exception; strict response parsing with skipped flags.
- `read-pipeline-extraction-ladder` — version-first bytes; docx shares the edit matcher's flattener; sentinel strings never throw.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source excerpt, invariant, byte-exact Probe against the repo checkout (`cd /mnt/hdd/utopia/inspo/external/mike/backend`), and `search_graph` Retrieve against project `ext-mike`. Keep the canonical pinned commit; never vendor modules.

## Provenance
mike (MikeOSS legal-AI platform), AGPL-3.0 — **patterns-only**: adopt behavior contracts, never copy code verbatim into non-AGPL hosts. main @ `3ad9a5ffafd6ad21624a7c11a23188d3dc674b7d`; Codebase Memory project `ext-mike` (7,357 nodes / 25,035 edges, FULL mode @ same HEAD = base_sha, zero drift; parse_partial x60 confined to SQL migrations/CSS/test fixtures — none cited). Pass 1 whole-file mined backend planes: lib/{access,audit,privateIp,downloadTokens}, chat/{citations,contextBuilders,routeStreaming,stream­ing,verifyCitations,types}, chat/tools/{toolDispatcher,documentOps,courtlistenerTurnState}, middleware/auth (~7,400 LOC).

## Full view (memory graph)
Graph `ext-mike` resolves every cited seam line-exact via `search_graph --project ext-mike --query <symbol>` (BM25 over Function/Type nodes; Route nodes carry HTTP surfaces). Direct suites live beside their modules (`src/lib/__tests__/*.test.ts`, `src/lib/chat/*.test.ts`, `src/lib/chat/__tests__/`, `src/lib/chat/tools/*.test.ts`) and run with `bunx vitest run <file>` from `backend/`. SIMILAR_TO edges cluster the generate_* family (docx/xlsx/ppt) sharing `registerGeneratedDocument`.

## Boundaries
Adopt the fence-neutralize-verify pipeline (spotlight everything user-controlled; verify quotes server-side; swap drifted text), the upload-before-insert durability order with compensating deletes, and the reserved-row persistence protocol as portable contracts. Adapt limits (300-char audit titles, 200k context cap, 3-quote ceiling, 12-item ask_inputs), storage/table names, and event-type vocabulary to your host. Omit the Next.js frontend, Word add-in plane, e2e/loadtest harness, CourtListener provider internals beyond the turn-cache contract, and the MFA assurance ladder (queued pass-2 with courtlistenerTools) — none are part of the seams mined here.
