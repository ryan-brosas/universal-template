<!-- capsule-v2 -->
# Wait-for-condition ladder — how do you block an agent until a pane matches text/regex/goes idle, bounded by a timeout, against a live PTY?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the minimal correct event-driven wait primitive over a shared terminal so agents stop polling capture-pane?

## Event-driven predicate wait with idle + timeout + exit resolution
**Path/Symbol:** `packages/server/src/session-command-executor.ts:SessionCommandExecutor.waitFor` (:29–90); HTTP shape `POST /sessions/:id/wait` (`index.ts`:827–839) with `waitInputSchema` discriminated union (`schemas.ts`:259–282: `text|regex|idle`) and `buildWaitPredicate` (`index.ts`:501–522). Exposed as `SessionManager.waitFor` (`session-manager.ts`:717–727).
**Signature:** `waitFor(managed: ManagedSession, predicate: { kind: "text"|"regex"|"idle"; test(text: string): boolean }, timeoutMs: number, idleMs?: number): Promise<WaitResult>` where `WaitResult = { matched: boolean; elapsedMs: number; snapshot: string }`.
**Data Shape:** `idleMs` only passed for idle mode (HTTP default `SESSION_ACTIVITY_WINDOW_MS=750`, constants.ts:435; schema bounds 50–5000ms); `timeoutMs` defaults `WAIT_DEFAULT_TIMEOUT_MS=30_000` (constants.ts:929), max `WAIT_MAX_TIMEOUT_MS`. The predicate tests the CAPTURE-RENDERER grid — ANSI-processed text identical to what `capture-pane` returns — never raw PTY bytes.

### Decisive source
```ts
// :56-60 — every evaluation flushes the renderer first: the read never
// lands before the parser caught up (xterm parses writes on a timer).
const testPredicate = async (): Promise<boolean> => {
  const renderer = await this.ensureCaptureRenderer(managed);
  await renderer.flush();
  return predicate.test(renderer.capture());
};
const onOutput = (): void => {
  lastChangeAt = Date.now();
  void testPredicate().then((hit) => { if (hit && !resolved) finalize(true); });
};
// :73-77 — idle mode polls recency ONLY; the output listener bumps lastChangeAt,
// so no renderer read is forced each tick.
if (predicate.kind === "idle") {
  idleTimer = setInterval(() => {
    if (!resolved && Date.now() - lastChangeAt >= (idleMs ?? 0)) finalize(true);
  }, WAIT_IDLE_POLL_INTERVAL_MS);
```

**Flow:** attach → text/regex: one up-front evaluation (:81–83) in case the pane ALREADY matches, then re-evaluate on every `output` event → idle: 100ms interval (`WAIT_IDLE_POLL_INTERVAL_MS`, constants.ts:931) comparing now − `lastChangeAt` ≥ idleMs → timeout handle resolves `{matched:false}` at deadline → `exit` event resolves `{matched:false}` if the shell dies first → single `finalize` (guarded by the `resolved` latch) clears both timers, detaches BOTH listeners, captures a final pane snapshot (`catch(() => "")` — snapshot loss must not lose the result) and resolves with elapsed time. All timers `.unref()`'d.

**Invariant:** exactly ONE resolution wins and every path funnels through the same idempotent `finalize`; predicate evaluation is always flush-before-read so a match decision is never made on stale grid state; idle detection measures output RECENCY (event-timestamped), not renderer content; a waiter never outlives its session (exit listener).

**Probe:** `packages/server/tests/session-automation.test.ts` — :114 writeInputById then waitFor text ⇒ matched:true AND snapshot contains needle; :124 regex `/code-\d+/`; :133 never-matching needle with 200ms timeout ⇒ matched:false, elapsedMs ≥150; :142 idle mode with idleMs=100 after an echo burst ⇒ matched:true; :152 unknown id ⇒ null from the manager gate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "waitFor", file_pattern: "session-command-executor", fields: ["lines"], limit: 10 });
```

## Verdict
Adopt the three-mode predicate ladder (up-front text/regex eval, recency-based idle poll, exit-aware timeout), the resolved-latch single-finalize discipline, and flush-before-read evaluation on top of your existing headless renderer; adapt schema shapes, default/max timeouts, and the idle window to host; omit the CDP-screenshot `waitForRenderLanded` variant (`session-automation.ts`:91–110) unless you need pixel-level settle for screenshots. Coverage caveat: probes cite on-disk vite-plus integration tests (excluded from graph index by design).
