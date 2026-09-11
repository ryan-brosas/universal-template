<!-- capsule-v2 -->
# Sync delegate path — how does a blocking delegation collect stdout, survive timeout/abort, and persist a result file the chat never has to carry?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** What must the synchronous (blocking) branch of a delegate tool do differently from the async branch so its result, error text, and persistence behave identically for the model?

## waitForChild → persistResult → formatSyncResult: three small contracts
**Path/Symbol:** `src/delegate-tool.ts`: `waitForChild` (:962-1000), `formatSyncResult` (:1002-1010), `persistResult` (:1111-1126); constant `SYNC_TIMEOUT_MS` :24. Sync call site: runDelegate tail :897-905.
**Signature:** `waitForChild(child, signal) -> Promise<{code,stdout,stderr,timedOut}>`; `persistResult(runId, body) -> Promise<file>`; `formatSyncResult(agent, runId, task, r, file) -> string`.
**Data Shape:** sync runs are NOT registered in the module-level `runs` Map — they have no runId-visible lifecycle, no waiter, no injection; the tool call itself is the delivery channel.

### Decisive source
```ts
// src/delegate-tool.ts:971-974 — timeout resolves, it does not throw
const timer = setTimeout(() => {
  child.kill("SIGTERM");
  finish({ code: null, stdout: "", stderr: stderrText, timedOut: true });
}, SYNC_TIMEOUT_MS);
// :900-903 (runDelegate tail) — failure surfaces STDERR, success surfaces STDOUT
const body =
  result.timedOut || result.code !== 0
    ? (result.stderr.trim() || "(no stderr)")
    : (result.stdout || "(no output)");
// :1111-1126 — persist is best-effort; "" means "could not be persisted"
```

**Flow:** buffer stdout chunks / accumulate stderr → SIGTERM at 5 min resolving `{code:null, timedOut:true}` (:971-974; never rejects — abort kills the child at :976-980 and close resolves normally) → on close resolve with trimmed stdout + stderr (:988-995) → caller picks stderr-first body on ANY failure (timeout or non-zero exit) else stdout with "(no output)" placeholder (:900-903) → `persistResult` writes `<runId>.out` under `tmpdir()/acp-delegate` returning "" on write error (:1111-1126) → header states completed/failed/timed out (:1002-1010); success renders file-pointer-only payload; failure embeds a truncated stderr block. The spawn `error` event (ENOENT/EPIPE) resolves via the same finish with `stderr = err.message` (:996-998).
**Invariant:** (1) the promise NEVER rejects — every failure mode becomes structured data; (2) failure bodies come from stderr, success from stdout — a port that always returns stdout hides child failures; (3) the full output ALWAYS lands in a file even on success, keeping the inline payload to a header+pointer; persist failure degrades to an honest "(result could not be persisted to a file)" line rather than losing the pointer contract.
**Probe:** `tests/delegate-tool.test.ts` (buildChildArgs mode tests :184/:195/:206 pin the sync `-p` selection that feeds this path); deterministic greps T1-T4 below pin waitForChild/persistResult/formatSyncResult structure (no dedicated upstream suite exists for the sync path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "waitForChild persistResult formatSyncResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: never-rejecting child collection, stderr-on-failure/stdout-on-success body selection, always-persist-plus-pointer, best-effort persist with honest degradation. Adapt the timeout constant and result-file directory to your host. Omit the runs-Map lifecycle entirely for sync calls — registering them adds waiter/injection state that can never fire.
