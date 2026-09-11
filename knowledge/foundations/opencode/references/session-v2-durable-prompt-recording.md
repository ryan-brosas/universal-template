<!-- capsule-v2 -->
# Session v2 durable prompt recording — how do you make a prompt endpoint idempotent by client-chosen message ID without letting ID reuse smuggle different payloads?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A client POSTs a prompt with its own message ID and may retry after a lost response. How does the v2 engine record the prompt durably so an exact retry is a no-op, a same-ID different-body request is a typed 409, and unfinished mutations (compact/wait) answer with honest 503s instead of fake success?

## Find-first admission + equivalence-gated conflict
**Path/Symbol:** `packages/core/src/session.ts` (`V2Session.prompt` :360-386, `OperationUnavailableError` :95-100, shell/skill/compact/wait stubs :386-425) + `packages/core/src/session/input.ts` (`admit` :41-81, `projectAdmitted` :83-115, `projectPrompted` :118-155, `equivalent`/`matchesPrompt` :191-207, `promoteSteers` :245-265, `promoteNextQueued` :268-290) + `packages/server/src/handlers/session.ts` (prompt catchTags :150-175, compact/wait 503 mapping :176-215).
**Signature:** `prompt({id?, sessionID, prompt, delivery?, resume?}) → Effect<Admitted, NotFoundError | PromptConflictError>`; `Admitted = {admittedSeq, id, sessionID, prompt, delivery, timeCreated, promotedSeq?}`; `SessionInputTable` row = `{id, session_id, admitted_seq, prompt, delivery, time_created, promoted_seq NULL until promoted}`.
**Data Shape:** HTTP success returns `{data: Admitted}`; conflict is protocol `ConflictError{message, resource: messageID}` with `httpApiStatus: 409` (protocol/src/errors.ts); unfinished ops are `ServiceUnavailableError{message, service: "session.<op>"}` with 503. Default delivery is `"steer"`; `resume !== false` wakes the execution runner.

### Decisive source
```ts
// core/session/input.ts:51-52 — idempotency is a find-first short-circuit:
const existing = yield* find(db, input.id)
if (existing !== undefined) return existing
// ...publish PromptAdmitted; event.durable === undefined → die("...missing aggregate sequence");
// catchDefect → find(db, input.id) again, return stored if present else re-die (:77-79)

// core/session.ts:374-382 — two distinct conflict gates:
Effect.catchDefect((defect) =>
  defect instanceof SessionInput.LifecycleConflict
    ? new PromptConflictError({ sessionID: input.sessionID, messageID })
    : Effect.die(defect),
)
if (!SessionInput.equivalent(admitted, expected))
  return yield* new PromptConflictError({ sessionID: input.sessionID, messageID })
if (input.resume !== false) yield* execution.wake(admitted.sessionID)
```

**Flow:** `V2Session.prompt` runs uninterruptible: get session (→404), resolve prompt (data-URI mime extraction, directory mime default), client ID or fresh ID, delivery default "steer". `admit` finds by ID first — a stored row returns as-is (exact retry). Otherwise it publishes `PromptAdmitted`; the durable aggregate sequence becomes `admittedSeq`, and a missing sequence dies. The projector `projectAdmitted` inserts with `onConflictDoNothing` and dies `LifecycleConflict` when the ID already exists in `SessionMessageTable` (an admitted row can never be projected after promotion) or when the insert returned no row (concurrent winner). Back in `prompt()`, `equivalent` compares delivery + sessionID + canonicalized prompt JSON — same ID with a different body fails here → 409 with `resource: messageID`. Only then does `wake(sessionID)` schedule execution, and only unless `resume === false`. When the runner processes the input it publishes `Prompted`; `projectPrompted` sets `promoted_seq` guarded by `isNull(promoted_seq)`, verifies `matchesProjection` (equivalence + timeCreated equality) on any already-stored row, and inserts late if admission was never projected. Promotion is asymmetric: `promoteSteers` publishes ALL pending steers with `admitted_seq <= cutoff` in ascending order, while `promoteNextQueued` publishes exactly ONE oldest queue row; both treat a `LifecycleConflict` on an already-promoted row as void (replay-safe). Unfinished mutations (shell/skill/compact/wait) always fail `OperationUnavailableError{operation}` → handler maps to 503 `ServiceUnavailableError{service: "session.<op>"}`.
**Invariant:** A message ID identifies exactly one durable prompt: same ID + same body replays to the identical `Admitted` record; same ID + different body is always 409, never an overwrite. Projection of an admitted row after promotion is a defect (LifecycleConflict), not a silent no-op. Wake is opt-out (`resume !== false`), so recording-only clients must say so explicitly. An API that exists before its implementation answers typed 503, never 200.
**Probe:** `packages/opencode/test/server/httpapi-session.test.ts:564-637` ("durably records one v2 prompt for exact message-ID retries" pins: first+retry both 200 with equal bodies, DB row `promoted_seq: null` while `resume:false`, then same ID different text → 409 with exact body `{_tag:"ConflictError", message:"Prompt message ID conflicts with an existing durable record: msg_http_prompt", resource:"msg_http_prompt"}`, then a waking prompt promotes to a `type:"user"` message within 10s); `:639-664` ("returns v2 public unavailable errors for unfinished session mutations" pins compact/wait → 503 with exact `ServiceUnavailableError` bodies). Source pin:
```bash
grep -n 'if (existing !== undefined) return existing' packages/core/src/session/input.ts
grep -n 'input.resume !== false' packages/core/src/session.ts
grep -n 'OperationUnavailableError({ operation' packages/core/src/session.ts
```
expect 1 + 1 + 4 hits (the four stub operations shell/skill/compact/wait).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionInput admit projectAdmitted projectPrompted promoteSteers promoteNextQueued LifecycleConflict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt find-first-by-client-ID admission with an equivalence gate as the idempotency contract for any durable command endpoint: replay returns the stored record, divergence is a typed 409 carrying the resource ID. Adopt projector-side lifecycle conflicts as defects (die) rather than silent skips — a divergent replay of the same event ID means the stream is corrupt. Adopt opt-out wake so fire-and-forget recording and scheduling are explicit choices, and adopt typed 503 stubs for API surface that ships before its implementation. Adapt the steer/queue promotion asymmetry (all-steers-below-cutoff vs one-queued-at-a-time) to your own concurrency model; omit the late-insert branch of projectPrompted if your event bus guarantees projection before acknowledgment. Direct tests read whole (httpapi-session.test.ts 1090L, pass 7); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
