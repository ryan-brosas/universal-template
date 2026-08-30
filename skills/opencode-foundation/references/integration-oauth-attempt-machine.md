<!-- capsule-v2 -->
# Integration OAuth attempt machine — how do you run a stateful OAuth flow with background auto-completion, single-flight completion, expiry scrubbing, and scope-safe cleanup?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A coding-agent host must support key, env-var, and OAuth connections per integration. OAuth has two shapes — "code" (user pastes an authorization code later) and "auto" (browser callback completes in the background). How do you keep attempt state consistent across concurrent complete/cancel/expire calls without leaking the authorization scope?

## Attempt state machine over one SynchronizedRef
**Path/Symbol:** `packages/core/src/integration.ts` (`attemptLifetime`/`terminalRetention`/`scrubInterval` :198-200, `PendingAttempt`/`TerminalAttempt` :207-227, `settle` :322-344, `scrub` :346-368, `connection.oauth` :419-455, `attempt.complete` :477-502, `attempt.cancel` :504-513).
**Signature:** `connection.oauth({integrationID, methodID, inputs, label?}) → Effect<Attempt, AuthorizationError>`; `attempt.complete({attemptID, code?}) → Effect<void, CodeRequiredError | AuthorizationError>`; `attempt.status(attemptID) → Effect<AttemptStatus>`; `attempt.cancel(attemptID) → Effect<void>`.
**Data Shape:** `AttemptEntry = PendingAttempt | TerminalAttempt` in one `Map<AttemptID, AttemptEntry>` inside a SynchronizedRef. Pending carries `{status:"pending", completing:boolean, authorization, integrationID, methodID, label?, scope: Closeable, time:{created, expires}}`; terminal carries `{status:"complete"|"failed"|"expired", message?, removeAt}`. `authorization` is `{url, instructions} & ({mode:"auto", callback: Effect<Credential.OAuth>} | {mode:"code", callback:(code)=>Effect})`.

### Decisive source
```ts
// integration.ts:434 + :483-496 — the completing latch is set inside modify, then re-checked after
completing: authorization.mode === "auto",          // auto attempts start completing immediately
// complete(): single-flight gate inside ONE SynchronizedRef.modify
const match = current.get(input.attemptID)
if (!match || match.status !== "pending" || match.completing) return [match, current]
if (match.authorization.mode === "code" && input.code === undefined) return [match, current]
return [match, new Map(current).set(input.attemptID, { ...match, completing: true })]
// ...after the modify:
if (attempt.completing) return yield* Effect.die(`OAuth attempt already completing: ${input.attemptID}`)
```

**Flow:** `oauth()` forks a Closeable scope from the layer scope, runs the implementation's `authorize(inputs)` with that scope (onExit closes it on failure), registers the pending entry with `expires = now + 10min`, and — for auto mode — forks `authorization.callback → settle(id, exit)` into the attempt scope with startImmediately. `settle()` flips pending→terminal inside ONE `SynchronizedRef.modify` (missing/already-terminal → no-op), then on success stores the credential via `credentials.create` (see credential-replace-on-create), publishes `ConnectionUpdated` + `Updated`, and closes the scope forked-in. `complete()` re-enters the same `settle` for code mode; a code-mode complete without a code raises `CodeRequiredError` and leaves the attempt open. `scrub()` runs every 30s: expired pendings become `expired` with their scopes closed, terminal entries are deleted after 1-minute retention. `cancel()` deletes a pending entry and closes its scope. Every implementation failure is mapped by `authorize()` into `AuthorizationError{cause}`; missing key/OAuth methods are `Effect.die` (defects, not typed errors).
**Invariant:** at most one settle wins per attempt — the `completing` latch is set inside the same modify that reads it, so a racing auto-callback and manual complete cannot both store a credential; a pending attempt always owns exactly one forked scope that settle/scrub/cancel each close exactly once; terminal entries are retained briefly for status reads, then scrubbed.
**Probe:** `packages/core/test/integration.test.ts` (349L, 9 `it.effect`): "completes code OAuth once and stores the credential" pins code-mode storage with the pasted code in metadata; "keeps code attempts open when the code is missing and closes them on cancel" pins CodeRequiredError leaving the scope open (`closed === false`) and cancel closing it; "completes auto OAuth in the background" pins status→complete without an explicit complete call; "expires abandoned OAuth attempts" pins `expires - created === 10 minutes` and TestClock-adjusted expiry closing the scope. Source pin:
```bash
grep -c 'attemptLifetime' packages/core/src/integration.ts   # expect 2
grep -c 'completing' packages/core/src/integration.ts        # expect 5
grep -c 'SynchronizedRef.modify' packages/core/src/integration.ts # expect 4
grep -c 'it.effect' packages/core/test/integration.test.ts   # expect 9
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Integration attempt settle completing SynchronizedRef pending terminal scope close oauth authorize refresh", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-map attempt state machine: one SynchronizedRef, a completing latch set inside modify, time-based expiry with a periodic scrub, and per-attempt forked scopes closed on every exit path. Adapt the lifetimes (10min/1min/30s) and the credential store behind settle; omit the Effect-specific scope/fork mechanics if your host has structured concurrency equivalents. Coverage caveat: the refresh path inside `connection.resolve` (expires-within-5-minutes → implementation.refresh → credentials.update, :394-404) is source-confirmed only — no direct test pins it at this pin; Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
