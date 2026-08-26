---
name: palmier-pro-foundation
description: "Use when porting an embedded agent runtime that drives a host app through tools — bounded tool-use run loops with orphan tool-result repair, provider-neutral SSE stream folding into UI snapshots, hostile-input tool-argument decoding, short-id round-trips between LLM and internal UUIDs, dual-origin (in-app + MCP) tool dispatch over one executor, and progressive-disclosure skill injection. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# PalmierPro: in-app agent runtime foundation

## Use this for
Use when porting an embedded agent runtime that drives a host app through tools — bounded tool-use run loops with orphan tool-result repair, provider-neutral SSE stream folding into UI snapshots, hostile-input tool-argument decoding, short-id round-trips between LLM and internal UUIDs, dual-origin (in-app + MCP) tool dispatch over one executor, and progressive-disclosure skill injection. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/agent-run-loop-contract.md` — how does a turn loop survive cancellation, refusal, and half-finished tool calls without corrupting the conversation?
- `references/stream-snapshot-coalescing.md` — how do token deltas become UI snapshots without flooding the main actor?
- `references/anthropic-sse-fold.md` — how does a raw Anthropic SSE byte stream fold into provider-neutral events?
- `references/tool-executor-envelope.md` — what must wrap every tool call: gates, read fencing, diff publication, telemetry?
- `references/tool-arg-decode-no-trap.md` — how are LLM-supplied arguments decoded without trapping on overflow or unknown keys?
- `references/short-id-roundtrip.md` — how do 8-char ids shown to the model resolve back to full UUIDs safely?
- `references/dual-origin-mcp-dispatch.md` — how does one executor serve both the in-app chat and external MCP clients?
- `references/skill-progressive-disclosure.md` — how are skills indexed into the prompt without loading bodies?
- `references/save-queue-serialization.md` — how do overlapping NSDocument saves serialize without writing a torn or stale snapshot?
- `references/async-write-main-unblock.md` — how does an off-main document write avoid deadlocking the AppKit main thread?
- `references/manifest-load-failure-preservation.md` — how does a save avoid clobbering an unreadable sidecar file with an empty replacement?
- `references/package-mutation-coordinator.md` — how do side-effecting media commits wait for in-flight saves without deadlocking or corrupting the package?
- `references/close-save-drain.md` — how do you guarantee the final save persists unedited-state changes and that a failed close-save refuses the close?
- `references/staged-media-commit-rebase-retry.md` — how does a media file land in the project package even while the project is being renamed mid-save?
- `references/registry-standardized-url-ledger.md` — what happens to registry mutations that race its async disk load, and what is the identity key?
- `references/package-layout-atomic-writes.md` — what write order keeps a directory-bundle document internally consistent across saves and Save As?

## Capsule map
- **Agent runtime** — `agent-run-loop-contract`: bounded loop; orphan tool-use repair synthesizes error results before the next API turn.
- **Agent runtime** — `stream-snapshot-coalescing`: actor reducer + 50 ms dirty-flag publish, first event immediate, `.bufferingNewest(1)`.
- **Provider clients** — `anthropic-sse-fold`: index-keyed pending tool JSON accumulation; empty input becomes `{}`.
- **Tool plane** — `tool-executor-envelope`: origin gating, project-focus/editor guards, timeline-read fencing vs non-agent mutation revision, before/after diff publish.
- **Tool plane** — `tool-arg-decode-no-trap`: strict unknown-key + non-finite rejection; safeInt/clampInt never trap.
- **Tool plane** — `short-id-roundtrip`: sorted-neighbor prefix map, floor 8, ambiguous prefix rejected, pre ∪ post universe on exit.
- **MCP surface** — `dual-origin-mcp-dispatch`: allow-listed MCP subset of the same tools; session-pinned project; activation on first recognized MCP call.
- **Skills** — `skill-progressive-disclosure`: lenient frontmatter parse, required name/description, index-only system-prompt injection.
- **Project persistence** — `save-queue-serialization`: FIFO SaveRequest queue over async AppKit saves; snapshot captured at dequeue so the latest state wins.
- **Project persistence** — `async-write-main-unblock`: defer-flagged exactly-once `unblockUserInteraction` on every write() exit; off-main no-snapshot throws but still unblocks (issue #402).
- **Project persistence** — `manifest-load-failure-preservation`: fail-open read flag → empty-manifest suppression at snapshot time → byte-preserving sidecar copy at write time.
- **Project persistence** — `package-mutation-coordinator`: savesInProgress/activeMutations counters; queued mutations commit FIFO on last-save success, cancel wholesale on failure without reopening closing.
- **Project persistence** — `close-save-drain`: unconditional ≥1 final save + dirty loop + idle wait; failed close-save resumes delegate selector with false.
- **Project persistence** — `staged-media-commit-rebase-retry`: target-capture + inside-closure standardizedURL revalidation + ≤3 retry; `workAlreadyAdmitted` for close-time admission.
- **Project persistence** — `registry-standardized-url-ledger`: park mutations during async load, replay onto loaded truth, one batched save; standardizedFileURL identity everywhere.
- **Project persistence** — `package-layout-atomic-writes`: primary-document-first ladder, per-file atomic writes, preserve-or-write sidecars, media-dir copy only on relocate.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
PalmierPro (GPL-3.0), `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory project `palmier-pro` (mode full @ generation 2026-08-25T19:59:55Z, 13,620 nodes / 95,948 edges, skipped 0; 31 parse-partial files — pass-2 cited flagged ranges in VideoProject.swift, VideoProjectWriteUnblockTests.swift, and EditorViewModel+MediaLibrary.swift were read directly; 52 binary assets excluded by design). Pass 1: agent runtime/tool plane (8 capsules). Pass 2 (2026-08-26): project-document persistence & save coordination (+8 capsules).

## Full view (memory graph)
Revalidate `palmier-pro` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Tests live under `Tests/PalmierProTests/Agent/` (Swift Testing); no Linux runner exists for this macOS target — treat direct test reads as ground truth and record execution as blocked.

## Boundaries
Adopt the pure contracts: run-loop stop-reason algebra, orphan-repair rule, snapshot coalescing shape, arg-decoding guards, short-id prefix math. Adapt the host integration points: EditorViewModel fencing hooks, ToolDefinitions schema registry, SkillStore sync targets, analytics/telemetry capture. Omit PalmierPro product behavior: Convex-hosted model catalog, hosted PalmierClient proxy transport, editor UI panels, export/generation pipelines.
