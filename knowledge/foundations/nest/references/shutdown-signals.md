<!-- capsule-v2 -->
# Shutdown signal handling — how does an app run destroy→shutdown hooks exactly once per signal and still let the process die naturally?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the signal-latch/re-raise protocol that avoids double teardown and listener leaks?

## NestApplicationContext.listenToShutdownSignals
**Path/Symbol:** `packages/core/nest-application-context.ts:listenToShutdownSignals` (357-401), `enableShutdownHooks` (316-336), `unsubscribeFromProcessSignals` (406-413).
**Signature:** `listenToShutdownSignals(signals: string[], options?: { useProcessExit?: boolean })`.
**Data Shape:** `activeShutdownSignals: string[]` accumulates registered signals; `shutdownCleanupRef` holds the SAME function reference passed to process.on (required for removal).

### Decisive source
```ts
let receivedSignal = false;
const cleanup = async (signal: string) => {
  try {
    if (receivedSignal) return;          // LATCH: ignore signals while already shutting down
    receivedSignal = true;
    await this.initializationPromise;    // never tear down a half-booted app
    await this.prepareClose();
    await this.callDestroyHook();        // reverse-order module destroy
    await this.callBeforeShutdownHook(signal);
    await this.dispose();
    await this.callShutdownHook(signal);
    signals.forEach(sig => process.removeListener(sig, cleanup));
    if (options.useProcessExit) {
      process.exit(0);   // flushes async logger buffers via the 'exit' event
    } else {
      process.kill(process.pid, signal); // RE-RAISE so default disposition applies
    }
  } catch (err) {
    Logger.error(MESSAGES.ERROR_DURING_SHUTDOWN, err?.stack, ...);
    process.exit(1);
  }
};
```

**Flow:** enableShutdownHooks dedups + uppercases signals, filters already-active → registers cleanup on each → on signal: latch → await init → hook ladder → remove listeners → re-raise or exit.
**Invariant:** The same `cleanup` reference must be used for on/remove (anonymous wrappers leak). Hooks run in init-completion order guarantee (`await initializationPromise`). Error during shutdown exits 1 rather than hanging. Duplicate enable calls are idempotent via the active-signals filter.
**Probe:** `packages/core/test/nest-application-context.spec.ts::listenToShutdownSignals` (:56).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "listenToShutdownSignals receivedSignal useProcessExit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the latch + await-init + hook-ladder + re-raise protocol; adapt signal names/exit codes to your runtime; omit useProcessExit unless you carry buffered-async-loggers. Porting wrong: re-raising without removing listeners first loops teardown forever; skipping the init await tears down providers mid-bootstrap.
