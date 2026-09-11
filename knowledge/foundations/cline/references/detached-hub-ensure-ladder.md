<!-- capsule-v2 -->
# Detached daemon ensure ladder — spawn-or-attach state machine that must never double-spawn onto a live port

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When a client needs "a compatible local daemon at this endpoint", what is the decision order among attach / repair / retire / spawn, and which outcomes must throw instead of spawning?

## discover → verify → attach | retire-incompatible | repair-discovery | spawn+poll
**Path/Symbol:** `sdk/packages/core/src/hub/daemon/index.ts:433-675` (`ensureDetachedHubServerLocked`, called under the startup lock).
**Signature:** `(owner: HubOwnerContext, workspaceRoot: string, endpointOverrides & {allowPortFallback?}) → Promise<DetachedHubResolution {url, authToken}>`.
**Data Shape:** Discovery record + probe result (`safeProbeHubServer(url[, token])`) + `verifyHubConnection(url,{authToken})`; managed URLs are remembered via `rememberRecoverableLocalHubUrl` only when the endpoint was NOT explicit.

### Decisive source
```ts
const superseded = discovered?.url ? undefined : readSupersededHubDiscovery(...);
if (discovered?.url) {
    if (!discoveredAuthToken) { retiredUnusableDiscovery = true; await retireDiscoveredHub(discovered, ...); }
    else if (healthy && isReusableHubRecord(healthy) && await verifyHubConnection(healthy.url, {authToken}))
        { return rememberIfManaged({url: healthy.url, authToken}); }          // 1 ATTACH
    // healthy but incompatible:
    const outcome = await retireIncompatibleHub({...healthy, authToken}, ...);
    if (outcome === "deferred_busy" && await verifyHubConnection(...))
        { return rememberIfManaged({...}); }   // 2 BUSY older hub => attach, never ambush
}
if (expected?.url && isReusableHubRecord(expected)) {
    // Live reusable hub, missing discovery: try every candidate token...
    const candidateTokens = [expected.authToken, discovered?.authToken, superseded?.authToken]...
    for (const token of candidateTokens) {
        if (!(await verifyHubConnection(expected.url, {authToken: token}))) continue;
        await writeHubDiscovery(owner.discoveryPath, repaired).catch(() => {}); // 3 REPAIR (best-effort)
        return rememberIfManaged({url: expected.url, authToken: token});
    }
    throw new Error(`A compatible Cline Hub is already running at ${expectedUrl}, ... Run 'cline doctor fix' ...`);
}
...
await spawnDetachedHubServerWithRetry(workspaceRoot, spawnEndpoint);   // port 0 when fallback allowed
while (Date.now() < deadline) { /* poll discovery+health+verify; also re-check expected URL for an incompatible squatter */ await sleep(HUB_STARTUP_POLL_MS); }
throw new Error("Timed out waiting for detached hub startup.");
```

**Flow:** (0) retire legacy shared hub; read discovery. (1) Discovered hub with token: probe + reusability + connection verify ⇒ attach. (2) Healthy-but-incompatible: retire; `deferred_busy` (still serving sessions) ⇒ attach to it rather than race it for the port. Record with no token ⇒ retire first (a bare port probe carries no auth/pid — the postinstall ".superseded" sidecar exists so pre-3.0.55 updaters cannot restart a busy hub). (3) Expected-URL probe without discovery: token-candidate loop over live/superseded records; first verifying token REPAIRS the discovery file (best-effort) and attaches; no token verifies ⇒ actionable error (with upgrade-specific hint about empty-token builds), never a second spawn. (4) Nothing usable: spawn detached (port 0 when `allowPortFallback`), then poll until deadline — each iteration re-reads discovery AND re-probes the expected URL to catch a squatter that appeared mid-wait. Explicit endpoints skip the recoverable-URL memory.
**Invariant:** At most one daemon ever owns an endpoint: a live compatible hub is attached to or repaired, not duplicated; retirement of a busy hub is deferred, not forced; all failure modes surface as errors naming the repair path ("cline doctor fix") rather than silent second spawns.
**Probe:** `grep -cF 'readSupersededHubDiscovery(owner.discoveryPath);' sdk/packages/core/src/hub/daemon/index.ts` → 1; `grep -cF 'throw new Error("Timed out waiting for detached hub startup.");' ...` → 1; `grep -cF 'rememberRecoverableLocalHubUrl(result.url, result.authToken);' ...` → 1. Direct tests: `daemon/index.test.ts` — "attaches to an older hub that is still serving sessions instead of retiring it", "reuses a healthy hub from a newer build without retiring it", "repairs discovery and attaches when a live hub can be authenticated", "throws when a compatible expected hub has no discovery record", "does not spawn another detached daemon from inside the hub daemon process".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "ensureDetachedHubServerLocked spawnDetachedHubServerWithRetry verifyHubConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the arm order attach→defer-busy→repair→spawn+poll and the "never spawn onto a verified-live port" rule with token-candidate repair. Adapt endpoint option plumbing, superseded-record policy, and error copy. Omit npm-postinstall-specific superseding. Runner-BLOCKED here (no node_modules); 17 named upstream cases pinned via source inspection.
