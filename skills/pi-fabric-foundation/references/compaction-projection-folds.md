<!-- capsule-v2 -->
# Compaction projections — how do you fold a whole session into fixed sections with stable references and zero remembered state?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does a deterministic summarizer keep salience computed (never stored) and every omission re-findable?

## Pure section folds over the typed event stream
**Path/Symbol:** `src/compaction/projections.ts:projectWithMetadata` (:651-677); folds `projectGoal` (:216-251), `projectFiles` (:260-332), `projectActivity` (:342-388), `projectOutstandingWithMetadata` (:400-461), `projectEarlierTurns` (:476-536), `projectStatus` (:541-576), `projectTranscript` (:596-649); operation join `collectOperations` (:118-173).
**Signature:** `project(events: CompactionEvent[]): Sections{goal,files,activity,outstanding,earlierTurns,status,transcript}` (+ `projectWithMetadata` adding per-section omittedCounts). Header comment states the design: salience is *computed* from the event stream by the outstanding fold's state machine — nothing is remembered, only re-derived.
**Data Shape:** every sampled line ends in `[entry <id>]`; omissions render as an omission line carrying FIRST+LAST entry ids of the dropped span; transcript lines carry stable `(#{index})` refs.

### Decisive source
```ts
// resolution is keyed ONLY by typed operation identity — never error prose
const keyOf = (operation) => {
  const path = isFileOperation(operation) ? pathOf(operation.args) : undefined;
  if (path) return `file\0${operation.tool}\0${path}`;
  const command = isBashOperation(operation) && typeof operation.args.command === "string"
    ? operation.args.command : undefined;
  if (command !== undefined) return `bash\0${operation.tool}\0${command}`;
  return `generic\0${operation.ref}\0${JSON.stringify(operation.args)}`;
};
const resolved = successes.some((s) => s.index > operation.index && s.key === key);
```
```ts
// fabric_exec calls appear ONCE per run: the completed run's summary replaces
// its raw call/result pair in the transcript window
const completedFabricCalls = new Set(events.filter(isFabricRun).map((e) => e.toolCallId));
if (event.kind === "toolCall")
  return event.name !== "fabric_exec" || !completedFabricCalls.has(event.toolCallId);
```

**Flow:** collectOperations joins toolResults to their toolCalls via toolCallId (fabricOperation events carry their own typed identity; bash events stand alone), sorted by index → Goal keeps ≤3 normalized lines of the FIRST user message; later scope changes become bounded one-liners through earliest/latest addressed sampling → Files lists only SUCCESSFUL file ops, bucketed created/written/modified/read (a write counts as Created only when the typed result proves it — `created === true` top-level or under details), deduped first-seen, reads hidden when the path was also modified, all rendered under a longest-common-path-prefix root → Outstanding pairs each failure with `[RESOLVED]` when a LATER success shares the exact identity key → Earlier Turns group per user/customMessage context with tool histograms and last fabricRun → Current Status surfaces last request/change/execution/note → Transcript renders the last 40 events as one-liners.
**Invariant:** pure functions of the event stream — same input, byte-identical sections (determinism is what makes compaction resumable and testable); no prose classification of errors anywhere ("does not infer timeout or abort outcomes from error prose" holds here too); every bounded list degrades via the shared earliest/latest sampler so the omitted middle always has an address range.
**Probe:** `tests/compaction.test.ts:901` ("keeps a file error open when a different action later succeeds on the same path"), `:920` ("marks a bash error [RESOLVED] when the same command is later re-run OK"), `:939` ("leaves an error open without classifying its prose when nothing resolves it"); fabric_exec single-appearance pinned via the qa suite (`tests/compaction-qa.test.ts:95-102` exercises the run/call/result trio).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "collectOperations projectOutstandingWithMetadata projectTranscript projectFiles sampleAddressedFrom omissionLine", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-fold architecture, typed identity keys for resolution, creation-proven write labeling, and the fabric_exec call/result suppression rule; adapt section set, line caps, and role vocabulary to your event schema; omit the pi-specific event kinds. Direct tests cited; graph coverage clean.
