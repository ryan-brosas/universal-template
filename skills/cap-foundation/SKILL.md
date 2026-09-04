---
name: cap-foundation
description: "Use when building a screen-recording pipeline: multi-track studio recording actor (pause/resume segmented), crash-safe fragmented MP4 recovery with manifest ladders, browser MediaRecorder spooling, streaming multipart upload with uncertain-completion semantics, getDisplayMedia retry ladders, and VFR-safe duration/sync invariants."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Cap Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `cap`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@0ce9e67516b14449c4263c0b173c85c40f30421b`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: StudioRecordingActorFsm;
  RequiredVsOptionalTrackFailure; CrossTrackStartTimeSnapping;
  VfrMediaSpanDuration; FragmentManifestRecoveryLadder;
  TmpRescueAndRespawnGroups; RecoveryStartTimeFallback;
  DisplaySyncSpanInvariant.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
