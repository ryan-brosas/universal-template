---
name: meetily-foundation
description: "Use when building local-first meeting-transcription summarizers, multi-provider LLM summary pipelines (chunk → combine → template → translate), English-canonical translation flows with result caching, or SQLite-backed regeneration with backup/restore — Meetily foundation."
---
# Meetily: meetily-foundation

## Use this for
Use when building local-first meeting-transcription summarizers, multi-provider LLM summary pipelines (chunk → combine → template → translate), English-canonical translation flows with result caching, or SQLite-backed regeneration with backup/restore. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/rust-english-canonical-pivot.md` — which final-language action runs per (summary_language, detected_language) pair and why pass 1 is always English.
- `references/rust-english-cache-reuse.md` — when a previous English summary is reused instead of regenerating pass 1 (ten-field source fingerprint).
- `references/rust-token-chunk-boundary.md` — token→char windowing math, `.max(1)` progress guarantee, sentence-then-word boundary snapping.
- `references/rust-cancellation-registry.md` — per-meeting CancellationToken registry and the `"cancelled"` error-substring protocol that must not be swallowed.
- `references/rust-context-threshold-ladder.md` — per-provider chunking thresholds (live metadata − 300, 1748/4000 fallbacks, 100000 cloud) and the double 300-token reserve.
- `references/rust-provider-wire-contract.md` — one client serving seven providers across two wire shapes; stale "60 seconds" timeout-message trap.
- `references/rust-builtin-sidecar-provider.md` — BuiltInAI early-return into a llama.cpp sidecar with required app_data_dir.
- `references/rust-weighted-language-detection.md` — char-weighted whatlang voting with a five-reason outcome taxonomy.
- `references/rust-llm-markdown-hygiene.md` — think-tag strip + paired-fence unwrap order and first-H1 meeting-name recovery.
- `references/rust-prompt-template-funnel.md` — three-stage prompt ladder over one Template object with tag-wrapped payload isolation.
- `references/rust-result-backup-restore.md` — `result_backup` SQL lifecycle: backup-on-reset, restore-on-fail/cancel, clear-on-complete.
- `references/rust-legacy-db-wal-recovery.md` — legacy .db adoption order, malformed/corrupt WAL retry ladder, TRUNCATE checkpoint on exit.
- `references/rust-meeting-folder-metadata.md` — per-meeting metadata.json language persistence with temp-rename atomicity.
- `references/rust-summary-command-entry.md` — Tauri command prelude: normalize → reset-with-backup → save transcript → spawn, immediate return.
- `references/py-ollama-chunk-size-override.md` — provider-conditional chunk-size override table and raw-schema Ollama path in the Python backend.
- `references/py-chunk-aggregation-merge.md` — extend-not-dedup section merge and the ≥1-chunk success bar.
- `references/py-summary-status-code-map.md` — /get-summary HTTP status ladder (202/200/400/500) and `_section_order` transform.
- `references/py-single-row-settings-and-key-ladder.md` — singleton settings rows, whitelisted API-key column maps, ALTER-on-startup schema validator.
- `references/py-transcript-save-search-dual-write.md` — segments-vs-whole-text dual representation and segments-first search dedup.
- `references/rust-dead-plane-map.md` — lib.rs as liveness oracle: audio_v2/*, stt.rs, *_old files look real but are NOT compiled.

## Capsule map
- **Summary language FSM** — `rust-english-canonical-pivot`: pass 1 always English; Translate hard-fails, Normalize soft-fails, cancellation re-raised.
- **English cache reuse** — `rust-english-cache-reuse`: FNV-1a+length fingerprints over ten source fields embedded in the stored result blob.
- **Chunking kernel** — `rust-token-chunk-boundary`: char-vector windows, step=max(size−overlap,1), rfind(". ") then ' ' backoff.
- **Cancellation** — `rust-cancellation-registry`: Lazy global HashMap<meeting_id, token>; raced against every LLM send; cleanup unconditional.
- **Threshold selection** — `rust-context-threshold-ladder`: ollama metadata −300 (fallback 4000), builtin registry −300 (fallback 1748), cloud 100000; chunk overlap fixed 100.
- **LLM wire dispatch** — `rust-provider-wire-contract`: Claude messages-API shape vs OpenAI-compatible shape; sampling params only for CustomOpenAI; timeout msg lies (300s).
- **Local sidecar** — `rust-builtin-sidecar-provider`: early-return generate_with_builtin; missing app_data_dir is a hard error; separate graceful/force shutdown.
- **Language detection** — `rust-weighted-language-detection`: ≥20 alpha chars gate, reliability+0.25 confidence gate, meaningful-char votes, Tie on exact equality.
- **Markdown hygiene** — `rust-llm-markdown-hygiene`: dot-all think-tag regex, whole-string paired fence unwrap, first `# ` line names the meeting.
- **Prompt funnel** — `rust-prompt-template-funnel`: chunk/combine/final builders; `<tag>` isolation; template rendering fingerprinted for cache invalidation.
- **Regeneration safety** — `rust-result-backup-restore`: upsert copies result→result_backup; COALESCE restore on failed/cancelled; clear on completed.
- **DB lifecycle** — `rust-legacy-db-wal-recovery`: copy .db before open; delete orphaned -wal/-shm on "malformed|corrupt" and retry once; PRAGMA wal_checkpoint(TRUNCATE) at exit.
- **Folder metadata** — `rust-meeting-folder-metadata`: metadata.json beside meeting folder; detected-language reuse beats re-detection.
- **Command entry** — `rust-summary-command-entry`: trim-empty⇒None normalization, daily_standup default, reset+save before spawn, immediate process_id return.
- **Python chunk override** — `py-ollama-chunk-size-override`: phi4*/llama* ⇒ 10000/1000 else 30000/1000; degenerate-overlap clamp.
- **Python merge** — `py-chunk-aggregation-merge`: blocks extend across chunks; MeetingNotes sections dedupe by title; empty list ⇒ status failed.
- **Python status map** — `py-summary-status-code-map`: double json.loads guard; data only on completed; _section_order preserves render order.
- **Python settings** — `py-single-row-settings-and-key-ladder`: id='1' singletons; whitelist-before-fstring key columns; try-ALTER migrations validated at startup.
- **Python transcripts** — `py-transcript-save-search-dual-write`: segment rows with audio_start/end/duration for playback sync; chunks row = LLM input; search dedups via NOT IN.
- **Dead planes** — `rust-dead-plane-map`: audio_v2/stt/_old files absent from lib.rs mod tree; graph nodes for them are historical metadata.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Before mining any Rust seam, check it against `rust-dead-plane-map` — cite only modules reachable from lib.rs.

## Provenance
meetily (MIT, Zackriya Solutions), `main@0281737d87d26352fb0adc78c8c0975f691b23d1` (=base_sha, zero drift at authoring); Codebase Memory project `ext-meetily` (root `/mnt/hdd/utopia/inspo/external/meetily`, branch main, FULL mode, 6,811 nodes / 26,090 edges, generation 2026-08-23T11:50:20Z generation_matches=true; parse_partial ×7 none cited; whisper.cpp/.cargo/logs excluded by design). Graph contains DEAD-CODE nodes under src/audio/ + src/audio_v2/ — see rust-dead-plane-map before trusting hits there.

## Full view (memory graph)
Revalidate `ext-meetily` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Recorded: head==base==`0281737d`; coverage stdin-JSON ×12 cited paths all `no_recorded_issue`+`metadata_match`; BM25 retrieval verified live for all capsule Retrieve anchors (note: dead-file symbols like `cleanup_overlap` also resolve — route by rust-dead-plane-map first). Behavior pressure: deterministic battery `/tmp/drain-collabdocs-meetily-p1-battery.sh` 45/45 green after correcting 12 probe defects against live source; Rust unit suites exist in-tree (`cargo test`, processor.rs/language_detection.rs) but no cargo toolchain run was performed this pass — recorded as runner caveat, not fabricated. Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts (language FSM, cache fingerprinting, backup SQL lifecycle, chunk windowing, detection taxonomy); adapt host-specific integration (Tauri commands, FastAPI endpoints, sidecar binary paths, provider constants); omit product surface (Next.js UI, tray/analytics/onboarding commands, whisper.cpp server packaging, docker scripts) and every uncompiled plane per rust-dead-plane-map.
