<!-- capsule-v2 -->
# Probe verdict classifier — which server answers to a `server/discover` probe are era evidence, and which are never?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Given one raw probe exchange (result / rpc-error / http-error / network-error / auth / close / timeout), how does a client decide: modern, corrective retry, legacy fallback, or typed error?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/probeClassifier.ts`: `classifyProbeOutcome` (:129-183), `classifyResult` (:185-210), `classifyRpcError` (:212-245), `classifyHttpError` (:247-302), `classifyNetworkError` (:304-316), `NOT_PROBE_RECOGNIZED = {-32001,-32020,-32021}` (:123).
**Signature:** `classifyProbeOutcome(outcome: ProbeOutcome, context: ProbeClassifierContext): ProbeVerdict` — pure; loop-guard and retry state live in the caller. Verdicts: `{kind:'modern',version,discover}` | `{kind:'corrective',version,error}` | `{kind:'legacy'}` | `{kind:'error',error}`.
**Data Shape:** Context carries `clientModernVersions`, `requestedVersion`, `fallbackAvailable`, `environment: 'node'|'browser'`, `transportKind: 'stdio'|'http'`. Deliberately conservative: anything not POSITIVELY recognized as modern resolves legacy.

### Decisive source
```ts
// Auth statuses are never era evidence … an auth wall must never enter era
// recovery — persisting a legacy verdict for it would recreate the
// silent-legacy bug at the fleet level.
if (outcome.status === 401 || outcome.status === 403) return { kind:'error', error: new SdkHttpError(...) };
if (outcome.status >= 500) return { kind:'error', ... };   // a 5xx body is the infrastructure's, not the handler's
// HTTP-rejected probes carry their JSON-RPC error in the body — classify like in-band.
if (code === -32_022) { /* mutual modern version ⇒ corrective (exactly once);
   disjoint-but-modern ⇒ typed error, NEVER initialize;
   legacy-only list ⇒ legacy when fallback available */ }
```

**Flow:** transport-aware rows: stdio timeout or child-exit-on-probe ⇒ LEGACY signal (servers built on SDKs that terminate on any pre-initialize request ARE legacy servers); HTTP timeout/close ⇒ typed error (deployed servers answer — silence is outage). Browser CORS opaque TypeError ⇒ legacy (the fallback's pre-2026 headers pass where the probe's could not); Node TypeError ⇒ error. `-32022` corrective runs exactly once even if the mutual version equals the just-rejected one.

**Invariant:** −32001/-32020/-32021 and every unrecognized code fall into the conservative legacy default — they are session/auth/ladder codes, never era evidence. Auth walls propagate as errors so finishAuth can run; converting them to legacy fallback would double-prompt and handshake an auth-gated modern server as legacy. An established modern connection is never demoted by later failures.

**Probe:** `packages/client/test/client/probeClassifier.test.ts` (35 tests incl. :237 "-32001 … never probe evidence", :291 "stdio: timeout is a legacy-server signal", :313 "browser environment + bare TypeError → legacy"); integration matrix in `test/integration/test/client/versionNegotiation.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "classifyProbeOutcome ProbeVerdict NOT_PROBE_RECOGNIZED", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the four-verdict taxonomy with transport/environment-aware rows and the never-evidence code set; adapt code literals to your protocol's assigned range; omit browser CORS handling for non-browser hosts.
