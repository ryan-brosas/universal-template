# crewai-foundation — union reconciliation record (2026-08-24, commit ddc2c6a3)

## What happened (concurrent-lane same-seam authoring, resolved as union)

Two cron lanes authored crewAI pass-1 simultaneously at the same pin
(`main@9e9a8577becc322f98a966ad88d7904251049744`, zero drift both sides):

- **Sibling lane** (drain-lane-pydantic-ai-frameworks): landed FIRST as
  `bda03b1d` with 19 wired refs + leaf + packs.json member #140 + router line +
  learning row `1|19|19`. Their commit message explicitly noted "22 alt-named
  refs present but UNWIRED at commit time — reconciliation queued next-pass"
  (they saw MY files mid-run and deferred).
- **This lane**: authored 34 repo-seam capsules + 5 cross-repo pattern capsules,
  wrote a full union leaf, then discovered the sibling closure had landed
  ~2 minutes before my write. Pivoted to UNION OWNER role per the
  concurrent-lane doctrine: committed only my leaf + 1 repaired ref.

## Union resolution details

1. **Kept every sibling ref on disk.** All 40 of their files were already
   capsule-v2 line-1 clean; quality-gate flagged them as orphaned because my
   draft leaf hadn't listed them. I adopted 20 of the 40 into the loader+map
   (the ones covering seams my own set didn't already own), keeping their text
   byte-intact.
2. **Replaced two of my overlapping seams with cross-repo versions** rather
   than deleting either author's file:
   - mine `event-scope-pairing.md` overwrote theirs (same filename) — theirs
     carried extra verified content (`event_scope` idempotent context manager,
     RAISE/WARN/IGNORE ladder, `resume_task_scope` max-sequence re-push) so my
     version now cites the `_prepare_event` pairing site (:553/:558) that theirs
     lacked, while preserving their anchors. Both Retrieve queries live-resolve.
   - racing/or-ledger overlap: kept BOTH granular seams (my fired-ledger +
     racing-first-wins split) AND their combined
     `or-listener-fire-once-rearm-racing.md`; all three are wired.
3. **Cross-repo pattern capsules shipped (5)** — the fleet's CROSS-REPO LINKER
   mandate:
   - xrepo-processwide-backend-setter (crewAI internal twin: lock_store ≅
     persistence factory)
   - xrepo-first-wins-racing (vs langgraph pregel FIRST_COMPLETED)
   - xrepo-appendonly-snapshot-ledger (internal: sqlite rows ≅ checkpoint
     filenames)
   - xrepo-event-scope-pairing (vs autogen envelope correlation)
   - xrepo-pause-as-return-hitl (vs agno approval gates + agency-swarm)
   - xrepo-copycontext-thread-hop (vs agno parallel fan-out deepcopy)
   All cross-repo claims verified against the named twin graphs this session;
   langgraph `_runner.py` FIRST_COMPLETED lines read directly from source.

## State at reconciliation close

- disk refs: **79** (39 wired by me incl. 20 adopted + 40 still pending their
  owner's wiring)
- loader lines: 39 · map entries: 39 · all 79 files v2 line-1 clean
- quality-gate rc0, ZERO crewai orphan warnings post-wire
- integrity OK 6 packs · hygiene failures all foreign (cron backup EOF,
  >1MB learning file debt, ell/htmx whitespace — none crewai)
- packs.json member #140 + desc + router line: sibling's, untouched, correct
- manifest.json entry: present

## For the NEXT pass (any lane)

The 40 unwired sibling-authored refs are GOOD CAPSULES needing only loader/map
lines. Wire them by group: crew-plane (crew-kickoff-scheduling,
crew-task-pipeline, step-executor-worker, todo-dependency-scheduler,
task-agent-handoff, replan-machinery, finalize-synthesis, planning-*,
planner-observation-parsing), tools-plane (tool-failure-protocol/-taxonomy,
tool-cache-and-limits/-opt-in, native-tool-batch, provider-tool-call-
normalization, react-parser, rpm-and-force-finish), llm/streaming plane
(llm-stop-param-recovery, reasoning-effort-ladder, prompt-cache-breakpoints,
stream-frame-pipeline, multimodal-file-injection, context-recovery-ladder),
flow-plane (flow-engine-loop-safety, flow-hooks-ladder,
executor-flow-state, state-copy-discipline, deterministic-fingerprints,
checkpoint-config-coercion, event-handler-dependency-graph, event-bus-dispatch,
human-feedback-rerun, plan-execute-flow-graph, flow-runtime-dag-engine vs my
granular set — dedupe-adjudicate before wiring).

After full wiring expect parity ~79=79=79 and update the learning row to
`1|79|79` (or pass-2 numbering if upstream drifts first).
