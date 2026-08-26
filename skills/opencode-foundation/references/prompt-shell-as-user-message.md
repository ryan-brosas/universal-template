<!-- capsule-v2 -->
# Shell-as-user-message — how is a user-run shell command recorded as an assistant tool call?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does user-executed shell produce the same transcript shape as a model-initiated bash call, and what must happen when it's aborted mid-stream?

## Synthetic transcript with streaming persistence
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`shellImpl`, lines 451–592).
**Signature:** `shellImpl(input: ShellInput, ready?: Latch.Latch): Effect<SessionV1.WithParts, never>` wrapped in `Effect.uninterruptibleMask`.
**Data Shape:** Writes FOUR records up front: synthetic user message + part "The following tool was executed by the user", then assistant message + running ToolPart (`tool: ShellID.ToolID`, `callID: ulid()`, input `{command}`). Spawn env: `TERM=dumb`, plugin-mutable `shellEnv.env` via `plugin.trigger("shell.env")`, `stdin: "ignore"`, `forceKillAfter: "3 seconds"`. Output accumulates in a closure string; while status==="running" each chunk updates `part.state.metadata = {output}` so UI streams live.

### Decisive source
```ts
// prompt.ts:580-586 — interrupt vs die discrimination decides the abort narrative
if (Exit.isFailure(exit) && Cause.hasInterrupts(exit.cause) && !Cause.hasDies(exit.cause)) {
  aborted = true
}
yield* finish   // uninterruptible finalizer:
// if (aborted) output += "\n\n<metadata>\nUser aborted the command\n</metadata>"
// completes message once (guard !msg.time.completed), flips running part → completed {output}
...
if (Exit.isFailure(exit) && !aborted && !Cause.hasInterruptsOnly(exit.cause)) {
  return yield* Effect.failCause(exit.cause)   // REAL failures propagate; aborts don't
}
```

**Flow:** ensureRunning via startShell (BusyError if another shell runs) → latch opens after scaffolding persisted (`Effect.ensuring(markReady)` so even failure releases waiters) → spawn through preferred shell config → stream-merge stdout+stderr into one `output` string, persisting metadata per chunk → on exit: interrupt-without-die ⇒ aborted narrative; real die/failure re-fails AFTER finish() has persisted state.
**Invariant:** The transcript must look identical whether the MODEL or the USER ran the command — history replay and permission audits see one shape. The finalizer is `Effect.uninterruptible`: cancel during teardown must still land completed/aborted part state or the session shows a forever-running tool. TERM-ignoring processes are handled by forceKillAfter escalation, and the aborted marker is appended regardless.
**Probe:** `packages/opencode/test/session/prompt.test.ts:1660` stderr captured into output AND metadata.output; `:1681` "running metadata before process exit" (polls "first" while process alive); `:1819` cancel ⇒ idle + "User aborted the command"; `:1859` trap''-TERM ignore STILL resolves success with abort narrative.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "session run state busy shell latch", limit: 8 });
```

## Verdict
Adopt synthetic-transcript equivalence, chunk-wise metadata streaming, uninterruptible finalize with abort-vs-die split; adapt spawner/env APIs; omit Shell.preferred arg-quoting internals (core util).
