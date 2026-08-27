---
name: openoats-foundation
description: "Use when porting a local-first recording/session store: canonical per-session directory layouts with permission-hardened atomic JSON writes, long-lived append file handles, delayed async-enrichment write draining before shutdown, destructive-overwrite backup ladders, time-windowed artifact retention, empty-\"ghost\" session reconciliation, abandoned-session resume election, user-tag updates that must preserve machine-namespaced tags, hostile-filename-safe attachment import with copy-before-metadata consistency, ordered finalize drain ladders with ghost collapse and typed recovery results, pure audio-retention/empty-session health plans, or session-selection state resets that preserve unsaved drafts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# OpenOats: session-storage kernel foundation

## Use this for
Use when porting a local-first recording/session store: canonical per-session directory layouts with permission-hardened atomic JSON writes, long-lived append file handles, delayed async-enrichment write draining before shutdown, destructive-overwrite backup ladders, time-windowed artifact retention, empty-"ghost" session reconciliation, abandoned-session resume election, user-tag updates that must preserve machine-namespaced tags, hostile-filename-safe attachment import with copy-before-metadata consistency, ordered finalize drain ladders with ghost collapse and typed recovery results, pure audio-retention/empty-session health plans, or session-selection state resets that preserve unsaved drafts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/session-canonical-layout-seeding.md` — what exactly does a new session persist, and with which durability/permission guarantees?
- `references/live-transcript-filehandle-lifecycle.md` — when is the live JSONL handle opened, kept open, and closed?
- `references/delayed-enrichment-pending-write-drain.md` — how do you await in-flight async enrichment writes before finalize/shutdown?
- `references/final-transcript-tmp-swap-prebatch-backup.md` — how is a destructive final-transcript overwrite made recoverable?
- `references/batch-audio-stash-rerun-window.md` — how are batch audio stems retained for reruns yet garbage-collected?
- `references/ghost-session-reconciliation.md` — when does an empty calendar-bearing session merge into a real one instead of lingering?
- `references/abandoned-session-resume-election.md` — which prior unfinished row may a restart resume instead of creating a duplicate?
- `references/internal-tag-preserving-update.md` — how do user tag edits avoid destroying importer-namespaced tags?
- `references/imported-manual-session-dedup.md` — how do you create non-recorded session rows without duplicating the one a calendar event already owns.
- `references/jsonl-tolerant-repair-backfill.md` — how do you fold late-arriving cleaned text into an append-only transcript without corrupting or losing lines.
- `references/notes-mirror-plane.md` — how do you export session notes to a user-chosen folder without blocking the actor or following malicious markdown links.
- `references/attachment-import-plaintext-export.md` — how do you import user files into a session store without letting hostile filenames or failed copies corrupt metadata?
- `references/finalize-consumer-ladder.md` — in what order must a live session be drained, exported, and collapsed before the UI is told it ended?
- `references/audio-retention-empty-session-classification.md` — how do you decide, from pure inputs, whether a session keeps its audio and what went wrong when it ended with zero text?
- `references/notes-selection-draft-plane.md` — how do you switch between sessions without losing an unsaved draft or leaking the previous session's state?

## Capsule map
- **Session layout & seeding** — `session-canonical-layout-seeding`: one actor owns `sessions/<id>/{session.json,transcript.live.jsonl,…}`; every metadata/JSONL write is `.atomic` then chmod 0600; IDs are timestamp-stamped `session_yyyy-MM-dd_HH-mm-ss`.
- **Live handle lifecycle** — `live-transcript-filehandle-lifecycle`: FileHandle created with 0600 attrs, seek-to-end, held open across all appends; closed only at finalize/start-of-next-session.
- **Pending-write drain** — `delayed-enrichment-pending-write-drain`: counter + CheckedContinuation waiters; waiters resume only at exactly zero, so awaiters observe fully enriched records.
- **Pre-batch backup ladder** — `final-transcript-tmp-swap-prebatch-backup`: tmp-atomic-write → remove → moveItem swap; non-empty final preferred over live as `transcript.pre-batch.jsonl`; recovery state recorded in metadata.
- **Batch audio rerun window** — `batch-audio-stash-rerun-window`: mic.caf/sys.caf/batch-meta.json stashed; init-time sweep deletes stems older than a 7-day modification-date window across canonical and legacy layouts.
- **Ghost reconciliation** — `ghost-session-reconciliation`: empty+artifact-free+calendar-bearing rows merge their calendar event into the nearest same-history-key real session within a gap budget, then delete themselves.
- **Resume election** — `abandoned-session-resume-election`: only unfinished/empty/artifact-free rows matching history key or exact calendar-event id within a max gap are resumable; exact event match wins ties.
- **Internal-tag preservation** — `internal-tag-preserving-update`: namespaced (`prefix:`) tags survive user-visible tag rewrites and stay ordered ahead of them; first legacy write migrates to canonical format.
- **Imported/manual session creation** — `imported-manual-session-dedup`: how do you create non-recorded session rows without duplicating the one a calendar event already owns.
- **JSONL tolerant repair** — `jsonl-tolerant-repair-backfill`: how do you fold late-arriving cleaned text into an append-only transcript without corrupting or losing lines.
- **Notes mirror plane** — `notes-mirror-plane`: how do you export session notes to a user-chosen folder without blocking the actor or following malicious markdown links.
- **Attachment import + export** — `attachment-import-plaintext-export`: UUID-prefixed sanitized storage names keep hostile filenames safe while displayName stays verbatim; the byte copy succeeds BEFORE any metadata append, so failures leave zero trace; exports render cleanedText ?? text per line.
- **Finalize consumer ladder** — `finalize-consumer-ladder`: numbered drain-before-mutate order (scratchpad → engine → cleaner → pending JSONL writes) before finalizeSession; ghost collapse reloads the effective index from the merged target and suppresses the recovery batch; recoveryResult is a closed four-value vocabulary.
- **Retention plan + classification** — `audio-retention-empty-session-classification`: pure plan where cloud-model ∧ zero-utterances forces a recovery batch that transitively forces audio retention; twin two-arm health ladders share their arms but differ only in fall-through (nil issue vs .unclassified telemetry).
- **Selection + draft plane** — `notes-selection-draft-plane`: every loaded field resets to defaults BEFORE async loads resolve (anti-leak); unsaved drafts park in a non-observed per-session map only while they differ from saved markdown.
## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenOats (MIT), `main@bc0ddb9d5d12e2ea4dddbc2c1b09e0c1ef708df7` (tag v1.84.4); Codebase Memory project `openoats` (FULL mode, ready, 5331 nodes / 26451 edges, gen 2026-08-25T19:59:34Z; cited paths no_recorded_issue + metadata_match).

## Full view (memory graph)
Revalidate `openoats` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Upstream direct tests are XCTest under `OpenOats/Tests/OpenOatsTests/` and require macOS 15 + Swift 6.2 toolchain (FluidAudio/WhisperKit/Sparkle deps) — they cannot execute on Linux hosts; treat Probes as upstream-executed contracts to re-run on a Mac.

## Boundaries
Adopt the storage contracts: canonical layout, atomic+0600 writes, pending-write drain protocol, pre-batch backup ladder, retention windows, reconciliation/resume predicates, tag namespace preservation. Adapt file-layout paths, date formats, and the actor isolation to your host language/runtime. Omit macOS-specific surfaces (security-scoped bookmarks, AppKit consumers), the WhisperKit/FluidAudio transcription engines, and the notes-mirror destination policy.
