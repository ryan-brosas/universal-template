<!-- capsule-v2 -->
# Watchdog exit-code taxonomy — the detached process-tree killer reports WHY it killed: 124 timeout, 143 cancellation, else child code/signal

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Your watchdog wrapper kills children on timeout and cancellation — what exit code should reach the parent so callers can distinguish "too slow" from "cancelled" from "the child itself failed"?

## child-process-watchdog.mjs
**Path/Symbol:** `src/handlers/child-process-watchdog.mjs` (whole file, 90 L); invocation `timeoutMs, cancellationPath|"-", command, …args`; consumed by `execChildPrompt` via `src/handlers/pi-child-process.ts:52` (`new URL("./child-process-watchdog.mjs", import.meta.url)`).
**Signature:** argv protocol `[timeoutValue, cancellationPath, command, ...args]`; invalid ⇒ stderr note + exit 2.
**Data Shape:** exit codes — 124 = timed out (GNU-convention), 143 = cancelled via sentinel (128+SIGTERM), child's own numeric code, or 1 for signal-death (SIGTERM⇒143 mapping only when not our cancellation), 127 = spawn error; stderr carries one-line reason prefixes.

### Decisive source
```js
const cancellationPoll = cancellationPath === "-" ? undefined : setInterval(() => {
  if (!existsSync(cancellationPath)) return;
  cancelled = true;                       // file-sentinel IPC: existence IS the message
  process.stderr.write("[pi-hermes-memory] child cancellation requested; terminating process tree\n");
  terminateTree();
}, 25);

child.once("close", (code, signal) => {
  clearTimeout(timeout); clearInterval(cancellationPoll); clearTimeout(forceTimer);
  if (timedOut)            process.exitCode = 124;
  else if (cancelled)      process.exitCode = 143;
  else if (typeof code === "number") process.exitCode = code;
  else                     process.exitCode = signal === "SIGTERM" ? 143 : 1;
});
```

**Flow:** watchdog spawns the command DETACHED (`process.platform !== "win32"`, group leader) piping stdio through → 25 ms polling of the cancel-file (existence-checked, never read) OR the timeout fires → `terminateTree()` is idempotent (`terminating` latch): SIGTERM to `-pid` (whole group; Windows: `taskkill /T /F`) then a `.unref()`'d 500 ms SIGKILL backstop → own SIGTERM/SIGINT handlers route through the same terminator → close handler assigns the taxonomy above.
**Invariant:** kill-reason must survive as DATA: callers text-match stderr and map codes (the override-failure retry ladder distinguishes provider auth failures from timeouts by exactly this). The latch prevents double-kill races between timeout/cancel/parent-signal; every timer/poll is `.unref()`'d or cleared so the watchdog cannot outlive its child. Pass 4 wave context: `session_shutdown` now AWAITS flushes (`session-flush-duality.md`), so cancellation-vs-timeout attribution is load-bearing for shutdown-latency debugging.
**Probe:** deterministic greps from repo root: `grep -c 'exitCode = 124' src/handlers/child-process-watchdog.mjs` → 1; `grep -c 'cancelled ? 143\|cancelled)      process.exitCode = 143' src/…` style checks collapse to: `grep -n 'timedOut) {' src/handlers/child-process-watchdog.mjs` resolves the close-handler branch (:78–86). Behavioral probe (upstream suite covers the wrapper): `npx tsx --test tests/handlers/session-flush.test.ts` GREEN — the abort-narrative expectations were realigned with the watchdog in ab9da66. Coverage caveat: the .mjs watchdog has NO direct unit test upstream (spawn-level behavior); its contract is pinned by grep + the consuming suites.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "signalTree terminateTree cancellationPath", limit: 5 })`

## Verdict
Adopt the code taxonomy + idempotent two-phase tree termination for any timeout/cancel wrapper around external processes. Adapt signal choices on Windows. Pair with `child-subprocess-transport.md` (how the parent interprets these exits) and `open-integrity-scan-deferral.md` (why startup stays cheap enough for awaits to be safe).
