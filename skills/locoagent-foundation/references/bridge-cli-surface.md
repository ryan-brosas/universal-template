<!-- capsule-v2 -->
# Bridge CLI surface — spawn-mode precedence ladder and headless daemon variant

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does an interactive orchestrator entrypoint validate flags against a runtime gate, persist mode preferences, and expose the same loop headlessly?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeMain.ts` — `parseArgs` (:1737-1887, cross-validation :1831-1853), gate-aware multi-session denial with telemetry flush (:2050-2076, 500ms flush cap :2066-2069), trust-dialog bypass requirement (:2084-2093), http-only-for-localhost guard (:2182-2193), saved-pref guard + first-run dialog (:2215-2276), **spawn-mode precedence ladder** (:2278-2306: resume > flag > saved > gate_default), resume flow env-mismatch fallback (:2363-2545 incl. dual-candidate reconnect :2498-2502 and no-deregister-on-transient comment :2524-2534), `w` toggle mutating config.spawnMode (:2621-2642), pointer write + hourly unref'd refresh (:2700-2729), `runBridgeHeadless` (:2810-2965) + `BridgeHeadlessPermanentError` (:2778-2783) + noop logger (:2968-2999).
**Signature:** `bridgeMain(args): Promise<void>` (exits via process.exit); `runBridgeHeadless(opts, signal): Promise<void>` (throws; permanent vs transient mapped by caller).
**Data Shape:** `SpawnMode = 'single-session' | 'worktree' | 'same-dir'`; maxSessions = 1 or `--capacity` (default 32).

### Decisive source
```ts
// Determine effective spawn mode.
// Precedence: resume > explicit --spawn > saved project pref > gate default
// - resuming via --continue / --session-id: always single-session (resume
//   targets one specific session in its original directory)
// - explicit --spawn flag: use that value directly (does not persist)
// - saved ProjectConfig.remoteControlSpawnMode: set by first-run dialog or `w`
// - default with gate on: same-dir (persistent multi-session, shared cwd)
// - default with gate off: single-session (unchanged legacy behavior)
...
if (resumePointerDir && isFatal) {
  // Clear pointer only on fatal reconnect failure. Transient failures
  // ("try running the same command again") should keep the pointer so
  // next launch re-prompts — that IS the retry mechanism.
```

**Flow:** parseArgs validates combinations WITHOUT the gate (async), bridgeMain checks the gate after enableConfigs/initSinks so the denial event can flush (explicit ≤500ms race — logEventAsync only enqueues and process.exit would discard it). Saved worktree pref in a non-git dir is cleared ON DISK so the warning doesn't repeat every launch. Resume: fetch session for environment_id → reuseEnvironmentId makes registration idempotent → backend may return a DIFFERENT env (expired): log sentry, warn, fall through to fresh-session creation rather than failing. Pointer lifecycle: written pre-loop, hourly mtime refresh, cleared at teardown EXCEPT the resumable-SIGINT early-return path where it backs the printed --continue hint. Headless variant: chdir + bootstrap-state set FIRST so git utilities resolve correctly; config errors throw BridgeHeadlessPermanentError (supervisor PARKS the worker) vs transient Errors (supervisor backoff-retries).

**Invariant:** (1) Gate-gated flags must fail with a flushed analytics event, not a silently-discarded one. (2) Preference persistence must be gate-guarded or a GrowthBook rollback leaves users on behavior the gate says is off. (3) Transient resume failures KEEP the crash pointer — the retry mechanism IS re-prompting. (4) Headless permanent-vs-transient is an error-TYPE contract with the supervisor, mirroring BridgeFatalError vs Error.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "Precedence: resume > explicit" src/bridge/bridgeMain.ts` (:2279); `grep -n "that IS the retry mechanism" src/bridge/bridgeMain.ts` (:2530); `grep -n "EXIT_CODE_PERMANENT" src/bridge/bridgeMain.ts` (:2776); graph resolves `locoagent.src.bridge.bridgeMain.parseArgs` :1737-1887 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bridgeMain runBridgeHeadless parseArgs BridgeHeadlessPermanentError spawnModeSource", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the precedence-ladder + preference-guard structure for any gated CLI surface; adopt the permanent/transient error contract for supervised daemons. Adapt flag names; omit readline dialogs in headless contexts entirely.
