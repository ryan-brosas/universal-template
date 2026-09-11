<!-- capsule-v2 -->
# Disposable-sibling stdio probe — how do you era-probe a server whose SDK kills the process on any pre-initialize request?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A stdio child has ONE process life; the probe is an unrecognized request that makes legacy servers exit. How do you probe without spending the session?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/versionNegotiation.ts`: `negotiateStdioViaSibling` (:601-651), `readStdioServerParams` (:578-588), `disposeSibling` (:660-668), `callerCloseAbortError` (:652-658); `negotiateEra` state machine (:453-576); spent-close-guard `disarmSpentCloseGuard` (:349-355).
**Signature:** `negotiateStdioViaSibling(negotiation, sessionTransport, params, deps): Promise<NegotiationResult>` — probes on a short-lived sibling spawned from the SAME params (`stderr: 'ignore'`); the caller's transport starts exactly once, after the era is known.
**Data Shape:** Sibling eligibility sniff: prototype must OWN `_dispose` (the SDK's own `StdioClientTransport` exactly; subclasses/custom stdio-shaped transports probe in place). Result = `{era:'modern',version,discover}` | `{era:'legacy'}`; typed `EraNegotiationFailed` abort when the caller closes mid-probe.

### Decisive source
```ts
// Dispose FIRST, with the close watch still armed: a caller close() landing
// during the disposal window must still trip the abort below — only once the
// sibling is reaped does the caller get its close back.
await disposeSibling(sibling);
sessionTransport.close = originalClose;
// The abort may orphan the probe promise; its late settlement (the disposed
// sibling's close, a timeout) must not surface anywhere.
negotiated.catch(() => {});
result = await Promise.race([negotiated, closedSignal]);
```

**Flow:** spawn sibling from same params → run `negotiateEra` on it (probe window open; inbound non-probe messages dropped with zero bytes written back) → verdict → reap sibling (signal escalation awaiting exit) → restore original `close` identity → only then start the session transport and hand over to `Protocol.connect()`.

**Invariant:** Closing an UNSTARTED transport records nothing, so `close` is monkey-patched for the window to convert a caller close into a prompt abort (racing the probe) instead of waiting out the timeout — checked AFTER the finally so a close during either the probe or disposal window still aborts, and the session transport is NEVER started in that case. Probe ids are strings and consume no Protocol message ids, so a legacy fallback's initialize is byte-equivalent to a plain legacy connect. A best-effort sibling that cannot be reaped must not turn a settled verdict into an error.

**Probe:** `test/integration/test/client/versionNegotiation.test.ts` :498 ("rmcp exit-on-probe: sibling spends itself and is reaped; the session connects legacy on its only spawn"), :521 ("modern server: the session adopts the sibling verdict — its wire carries neither server/discover nor initialize"); auth-seam propagation pins in `packages/client/test/client/probeAuthSeam.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "negotiateStdioViaSibling negotiateEra disarmSpentCloseGuard", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt disposable-sibling probing for any one-life subprocess speaking a negotiable protocol; adapt the sibling-eligibility sniff to your transport class; omit the close-monkey-patch if your transport records close-before-start.
