<!-- capsule-v2 -->
# Transient-error filtering twins — which in-stream error events are retry noise and which must fail the run?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** When a streaming CLI backend emits `error` events mid-run, how do you distinguish recoverable provider retries from terminal failures — and why must the pattern lists stay per-backend?

## Per-backend TRANSIENT_ERROR_PATTERNS gates
**Path/Symbol:** `src/backend/codex.ts` : patterns :223-227 + `isTransientError` :228-230, applied in `normalizeEvent` 'error' case (:206-216); twin at `src/backend/claude.ts` :191-200 applied BOTH in the 'result' case (`is_error === true`, filters `e.result`) AND the 'error' case (filters `e.error.message`). Companion suite: `tests/backend/transient-errors.test.ts`.
**Signature:** `function isTransientError(message: string): boolean`.
**Data Shape:** codex matches `/^Reconnecting\.\.\. \d+\/\d+$/` (anchored progress ticker); claude matches `/Retrying in \d+ seconds/i`, `/\(attempt \d+\/\d+\)/i`, `/API Error: Connection error/i`.

### Decisive source
```ts
// src/backend/claude.ts
case 'result': {
  if (e.is_error === true) {
    const errorMsg = (e.result as string) ?? 'Unknown error';
    // Filter transient errors (retry attempts)
    if (isTransientError(errorMsg)) { return null; }
    return { type: 'error', content: errorMsg, raw: event };
  }
  ...
// "Transients" become null: the event is DROPPED from the message stream,
// not converted into an error Message. The CLI keeps streaming; its own
// retry loop owns recovery.
```

**Flow:** every candidate error event string-matched against THAT backend's list → transient → return `null` (event vanishes; no Message emitted) → non-transient → `{type:'error', content}` propagates to consumers who fail the run/ensemble. The two backends NEVER share a list: codex's anchored `Reconnecting... n/m` ticker would false-positive-match nothing in claude's prose-style retries and vice versa — the dialects differ per CLI.
**Invariant:** filtering happens at NORMALIZATION time (per event), not at consumption time — downstream code can treat any emitted `error` Message as terminal without re-classifying. Dropping (null) rather than emitting a suppressed-error marker is deliberate: usage/done accounting stays untouched. Contrast with spawn-level ENOENT retry (`backend-spawn-retry.md`) which restarts the PROCESS; this plane only silences in-stream noise.
**Probe:** `tests/backend/transient-errors.test.ts` (20 pins over both dialects). Run: `bun test tests/backend/transient-errors.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"TRANSIENT_ERROR_PATTERNS reconnecting retry","limit":5,"detail":"ids"}'
```
→ resolves both pattern tables (`veda.src.backend.codex.TRANSIENT_ERROR_PATTERNS` etc.).

## Verdict
Adopt the normalize-time drop policy and one-pattern-list-per-backend rule verbatim. Adapt the regexes to your providers' actual retry chatter (re-derive against live streams before trusting these exact strings). Omit nothing else — the asymmetry IS the design.
