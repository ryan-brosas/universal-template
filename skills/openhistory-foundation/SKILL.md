---
name: openhistory-foundation
description: "Use when porting append-only JSONL event-store ingestion, bounded record schemas, incremental append caches with partial-write recovery, atomic in-place file rewrites, stateful privacy/redaction filters over timestamp-ordered event streams, task-episode segmentation with stable derived-record ids, provenance reconciliation of derived summary stores after source deletions, or evidence- calibrated LLM summarization gates that cap claims at what observations prove. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# OpenHistory: local activity-history ingestion, projection & privacy foundation

## Use this for
Use when porting append-only JSONL event-store ingestion, bounded record schemas,
incremental append caches with partial-write recovery, atomic in-place file
rewrites, stateful privacy/redaction filters over timestamp-ordered event
streams, task-episode segmentation with stable derived-record ids, provenance
reconciliation of derived summary stores after source deletions, or evidence-
calibrated LLM summarization gates that cap claims at what observations prove.
Source code and direct tests are ground truth; references carry decisive
excerpts and graph retrieval.

## Load the matching source dump
- `references/event-parse-gate.md` — how do untrusted JSONL lines become validated events without ever leaking protected ones into memory-visible output?
- `references/fail-soft-shard-loader.md` — how does a caller load the newest N events across daily shards without any error path escaping?
- `references/newest-first-id-dedup.md` — how do you stop reading once you hold the newest N unique events across many files?
- `references/append-cache-trailing-bytes.md` — how does a read cache stay correct when a writer appends mid-line between reads?
- `references/atomic-privacy-scrub.md` — how do you physically delete protected records from shard files without corrupting or losing malformed evidence?
- `references/sticky-privacy-boundary-filter.md` — how do you redact a *time interval* of activity, not just single events, while keeping the timeline shape readable?
- `references/gap-duration-boundary-segmentation.md` — where are the exact episode cut points (idle gap, max span, sleep/wake latch, privacy boundary), and which episode owns the terminator event?
- `references/episode-id-stability-digest.md` — what must an episode id be derived from so growing episodes never orphan already-persisted derived records?
- `references/work-window-trim-coalesce.md` — which context events survive into an episode, and when do repeated passive events collapse before summarization?
- `references/task-context-switch-signal.md` — when does a different-app or same-app context change start a NEW task without shattering rapid multi-app workflows?
- `references/pending-episode-admission-gate.md` — when is an episode ready to be summarized exactly once, and which inference failures skip one item vs abort the batch?
- `references/claim-ceiling-evidence-packet.md` — how do you convert telemetry into LLM briefs whose title verbs can never exceed the observed evidence?
- `references/derived-store-privacy-reconciliation.md` — after purging protected raw records, how do you cascade deletion through tiered derived stores by reproducing provenance?
- `references/owned-data-directory.md` — how do I claim, adopt, and delete an on-disk data directory without ever touching one we don't own.

## Capsule map
- **Parse gate** — `event-parse-gate`: zod-bounded line parse; protected events and malformed lines are both just `undefined`, so privacy filtering is unconditional at ingestion.
- **Fail-soft loader** — `fail-soft-shard-loader`: lexicographically sorted daily shards, timestamp sort, filter-then-slice double trim, catch→empty-array contract.
- **Bounded dedup walk** — `newest-first-id-dedup`: reversed file/event walk with first-wins id Map and labeled outer break at limit.
- **Append cache** — `append-cache-trailing-bytes`: size+mtime+capture-flag keyed per-file cache; range-read of appended bytes; last-newline split retaining an unterminated tail as carry bytes.
- **Atomic scrub** — `atomic-privacy-scrub`: pid-tagged 0600 temp file + rename rewrite that preserves unparsable lines verbatim and evicts the read cache.
- **Sticky boundary filter** — `sticky-privacy-boundary-filter`: per-browser-key enter/exit state sets emitting one-time sha256-id content-free `privacy_boundary` sentinels; exit markers are consumed.
- **Segmentation ladder** — `gap-duration-boundary-segmentation`: idle ≥5 min / span ≥13 min / sleep-lock latch / wake-unlock / quiet+switch cuts; terminators append-then-flush, openers flush-then-append; `privacy_boundary` cuts without entering an episode.
- **Episode identity** — `episode-id-stability-digest`: id anchored on the first WORK event's timestamp slug + sha256(id) digest, invariant while the live episode grows — stable foreign key for every derived store.
- **Evidence windowing** — `work-window-trim-coalesce`: trim to first-work −30 s lead … last work (+sleep/lock terminator), then collapse identical full-payload fingerprints inside per-kind horizons keeping the earliest.
- **Task-switch signal** — `task-context-switch-signal`: app-key change or same-kind same-app fingerprint divergence, evaluated only after ≥2 min quiet since the last work event.
- **Admission gate** — `pending-episode-admission-gate`: single-flight batch (cap 8), pending = unstored membership OR changed sourceEventIds, ≥8 min window + 60 s end quiet (or not-newest/sleep-ended); item-scoped inference errors skip one episode into a public lastError.
- **Claim ceiling** — `claim-ceiling-evidence-packet`: work units grouped by (app, durable object), additive priority weights (+80 draft/+120 submit/+1000 displayed result), claim-ceiling ladder with safe lead verbs and anti-overstatement boundary sentences; snapshot supersede by payload containment.
- **Reconciliation** — `derived-store-privacy-reconciliation`: scrub → re-segment once → keep only items whose provenance reproduces exactly (timeline ids+event ids; hours via sorted revision equality; rollups via revision-set membership); replaceAll unlinks orphan markdown and rewrites indexes atomically.
- **Owned data directory** — `owned-data-directory`: how do I claim, adopt, and delete an on-disk data directory without ever touching one we don't own.
## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenHistory (MIT), `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory project `openhistory` (full mode, generation 2026-08-25T20:10:30Z, 2543 nodes / 10791 edges; parse-partial caveats at `native/bridge/openhistory_native.c:242` and `src/renderer/src/App.tsx:864` — neither cited here). Pass 2 deepened the timeline-projection plane from NEXT-PASS TARGETS; pass 1 covered ingestion & privacy.

## Full view (memory graph)
Revalidate `openhistory` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts (parse gates, fail-soft loads, trailing-byte carry, atomic temp+rename rewrite, sticky interval redaction); adapt the capture-flag plumbing and Electron main-process wiring to your host; omit macOS-specific collectors (Swift accessibility reader), the Apple-adapter ML experiment scripts, and the native C bridge transport.
