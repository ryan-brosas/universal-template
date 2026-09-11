<!-- capsule-v2 -->
# Protocol-gate error laundering — when a headless child reports failure in side-channel JSON fields instead of the envelope's error key, how does the supervisor turn that into a run failure without losing partial output?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you collect failures from multiple response channels (envelope.error + per-protocol gate objects) into one terminal error while still persisting whatever text/usage the run did produce?

## Collect all channel errors, join with newlines, keep the record
**Path/Symbol:** `src/worker.ts:1117-1138` (Veda envelope normalization block; loop :1123-1132, join :1135-1138); failure propagation `terminalError` → `record.error` at :1181 (`if (terminalError) record.error = terminalError;`); success path unchanged (:1103-1116).
**Signature:** inline in the worker main loop: `const envelopeErrors: string[] = []` seeded with `stringField(vedaParsed.error)`, then one pass over gate keys `["design", "worker"] as const`.
**Data Shape:** gate value must be a plain object to count (`typeof gate !== "object" || gate === null || Array.isArray(gate)` → skip); failure means `status.ok === false` exactly (`ok !== false` → success, so `{}` or missing `ok` is NOT a failure); details come from EITHER `errors: string[]` (non-string entries filtered, joined `"; "`) OR `reason`+`detail` scalar fallback joined `": "` — never both; final message `` `Veda ${key} failed${details ? `: ${details}` : ""}` ``.

### Decisive source
```ts
// src/worker.ts:1117-1138 — multi-channel collection, then ONE join
const envelopeErrors: string[] = [];
const error = stringField(vedaParsed.error);
if (error) envelopeErrors.push(error);
// navigator-plan gates the response on a <program> design block and
// the worker persona on a <worker_report>; both exit non-zero and
// report failure only via design/worker fields, not envelope.error.
for (const key of ["design", "worker"] as const) {
  const gate = vedaParsed[key];
  if (typeof gate !== "object" || gate === null || Array.isArray(gate)) continue;
  const status = gate as Record<string, unknown>;
  if (status.ok !== false) continue;
  const details = Array.isArray(status.errors)
    ? status.errors.filter((entry): entry is string => typeof entry === "string").join("; ")
    : [stringField(status.reason), stringField(status.detail)]
        .filter((entry): entry is string => entry !== undefined)
        .join(": ");
  envelopeErrors.push(`Veda ${key} failed${details ? `: ${details}` : ""}`);
}
if (envelopeErrors.length > 0) {
  sawAgentError = true;
  terminalError = envelopeErrors.join("\n");
}
```

**Flow:** after process close, the accumulated Veda stdout is trimmed and parsed once (`parseStructuredValue`; unparseable stdout falls through to the generic stderr-reporting failed-record path) → `text`, `sessionId`, and `usage` are persisted FIRST regardless of later failure → every failure channel is drained into `envelopeErrors` → any collected error flips `sawAgentError` and becomes `terminalError` (newline-joined when multiple channels failed) → `record.error = terminalError` marks the run `failed`.
**Invariant:** protocol failure must not erase partial output — `record.text`/usage survive even when `design.ok === false` fails the run. Gate semantics are exact-match on `ok === false` (truthy-ok or absent-ok objects are ignored, arrays/null are skipped) so a chatty-but-successful envelope can't fabricate an error. The in-source comment is the contract: navigator-plan personas exit non-zero while reporting failure ONLY via `design`/`worker`, which is why `error` alone was insufficient pre-drift.
**Probe:** `tests/fixtures/fake-veda.mjs:23` (`case "design-fail"` prints `{text: "no program here", sessionId: "conv-1", usage: {...}, design: {ok: false, errors: ["[missing] no <program> block found"]}}` then exits 1) × `tests/worker-e2e.test.ts:176` (behavior `"design-fail"` expects status `failed` AND `r.error` matching both `/design failed/` and `/missing.*program/`) — proving partial text coexists with a laundered terminal error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "parseStructuredValue vedaOutput", limit: 10, fields: ["signature", "name", "file"] });
```
(The gate-drain block itself is anonymous inline code inside the worker's main arrow — BM25 cannot rank it; resolve `parseStructuredValue` (`src/worker.ts:175-196`, rank #1) and read the consumer region at :1117-1138.)

## Verdict
Adopt drain-all-channels-then-join for any child whose failure reporting is split across an error field and per-protocol result objects; keep persisting partial output before classifying the failure. Adapt the gate-key list and detail-shaping vocabulary (`errors[]` vs `reason`/`detail`) to your protocols; omit Veda persona specifics. Coverage caveat: pinned by the real-worker e2e suite (`skipIf(!hasWorker)`) plus the fixture itself; no standalone unit test isolates this block.
