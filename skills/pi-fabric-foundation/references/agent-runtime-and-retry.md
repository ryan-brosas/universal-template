<!-- capsule-v2 -->
# Bundled-runtime resolution + spawn monitor — how do you keep spawning JS workers when your own executable is a compiled bundle, and how do you tell "died at boot" from "crashed mid-run"?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** (a) which binary runs the worker when `process.execPath` is not node/bun? (b) which failures may be retried, and how is transport death detected without false positives?

## Runtime ladder + zero-progress retry gate + grace-window liveness
**Path/Symbol:** `src/agents/transports/process-utils.ts:88-128` (`resolveScriptRuntime*`, cached), `:145-170` (`spawnDetached`, negative-pid group kill); retry gate `src/agents/manager.ts:#retryStartup` (:973-1025); monitor `#monitor` (:1027-1122).
**Signature:** `resolveScriptRuntime(options?): Promise<string>`; `spawnDetached(workerPath, args, cwd): Promise<{pid, stop(), isAlive()}>`; `#retryStartup(managed, record, deadline): Promise<boolean>`.
**Data Shape:** constants (`src/agents/constants.ts`): poll 250ms, external liveness 2s, max attempts 3, base delay 500ms exponential; env override `PI_FABRIC_NODE_BINARY`; `requireNode` flag for Node-only worker flags.

### Decisive source
```ts
// (a) bundled pi binary cannot exec a .js module — resolve a real runtime
if (isGenericRuntime(execPath, requireNode)) return execPath;   // node|bun
const override = runtimeOverride(env);                          // PI_FABRIC_NODE_BINARY
for (const candidate of requireNode ? ["node"] : ["node", "bun"]) {
  if (await commandAvailable(candidate)) return candidate;
}
throw missingRuntimeError(execPath);
// (b) retry ONLY pre-first-turn failures with literally zero progress
record.status !== "failed" || record.turns !== 0 ||
record.toolCalls !== 0 || record.usage.input !== 0 /* ...all zero */ → no retry
```

**Flow:** spawn resolves runtime → argv `[runtime, worker.js, ...flags]` → detached with process-group SIGTERM (`-pid`) on stop → monitor polls status.json every 250ms; if the record says failed AND every progress counter is still zero, classify as startup failure → wait for transport exit, back off exponentially, relaunch via the SAME stored `launch` descriptor after wiping status/lifecycle files (attempts ≤3) → separately, an `isAlive()` false must persist for a full grace window before declaring "transport exited without a result" (transient poll blips never kill a run) → deadline expiry stops the transport first, then prefers a real terminal record over synthesizing `timed_out`.
**Invariant:** retries consume only *pre-turn, zero-usage* failures — anything that touched tokens or tools is deterministic and final; liveness uses a sustained-dead window (`firstObservedDeadAt` reset on any alive poll), not a single failed check.
**Probe:** `tests/script-runtime.test.ts:25,53,61` pin the runtime ladder incl. the loud error; `tests/agent-manager.test.ts:280` ("retries a Pi child that fails before its first turn", asserts `startup-attempts==2`), :298 (no retry for deterministic failure), :316/:335 (transport-death retry then give-up); `tests/bundled-binary-spawn.test.ts:42` pins end-to-end completion under a bundled execPath.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "resolveScriptRuntime retryStartup transport exited without result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the runtime ladder + zero-progress retry classification + sustained-dead window wholesale for any child-process agent runner; adapt the candidate list to your platforms; omit the sync variant if all callers are async. Rich direct tests across four suites — no coverage caveat.
