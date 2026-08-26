<!-- capsule-v2 -->
# Backend-split automation service — how does one thin REST client serve two backends without letting a multi-request mutation straddle a backend switch?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How does an SPA talk to either a local sidecar (axios) or a cloud host (proxy fetch) through one service class, and keep import's POST→PATCH→cleanup pinned to the backend that was active when the mutation started?

## Backend-split service + call-time interceptor
**Path/Symbol:** `src/api/automation-service/automation-service.api.ts` (`AutomationService`, module interceptor :83–111, `buildPinnedLocalConfig` :209–217, `createAutomation` :320–388).
**Signature:** `static async createAutomation(spec: AutomationSpec): Promise<Automation>`; `localAutomationAxios = axios.create()` + `interceptors.request.use(async (config) => …)`.
**Data Shape:** Every method reads `getActiveBackend().backend.kind` per call; `"cloud"` → `callCloudProxy({backend, method, path, body?, headers})`, else → `localAutomationAxios.<verb>(path, body?, config?)`. Headers are `{...AGENT_CANVAS_CLIENT_HEADERS, ...telemetryDistinctId?, ...extra}`.

### Decisive source
```ts
// Import uses an explicit baseURL/header pair so its POST, PATCH, and
// cleanup stay pinned to the backend selected when the mutation started.
if (config.baseURL) return config;

// Resolve the local backend on every call so it tracks the
// currently-active local backend … rather than freezing whatever value the
// agent-server-config produced at module load time. (#829)
const backend = getEffectiveLocalBackend();
if (!backend) throw new NoBackendAvailableError();
config.baseURL = backend.host;
const apiKey = backend.apiKey?.trim();
if (apiKey) config.headers.set("X-Session-API-Key", apiKey);
```

**Flow:** request → interceptor injects telemetry/client headers → explicit `baseURL` present? pin as-is : resolve registry now → verb call; cloud branch bypasses axios entirely via proxy.
**Invariant:** A single logical operation must never mix requests to two different hosts. The compensating import transaction creates with a unique placeholder event trigger (`pending.${crypto.randomUUID()}`, :155–163, :194–198) so the record is inert, PATCHes the real trigger + `enabled:false` together, and on PATCH failure DELETEs the inert record (:365–386); if cleanup also fails it throws `AggregateError([updateError, cleanupError], "Failed to disable…")` rather than the update error alone.
**Probe:** `src/api/automation-service/automation-service.api.test.ts` — "removes the inert automation when disabling it fails" (:331) asserts the delete carries the same pinned `{baseURL, X-Session-API-Key}` config; "fetches the cloud automation SDK version…" (:117) asserts the `X-Org-Id` header on the proxy branch.

### Secondary invariants worth porting
- Fail-soft probes: `getSdkVersion`/`checkHealth` catch everything → `null` / `{status:"error"}` with 5 s timeouts on BOTH branches (:246–272, :762–787); version accepted as `string | {sdk_version|version}` normalized trim-or-null (:113–129).
- Binary upload bypass: for cloud, `uploadAutomationTarball` skips the proxy because the cloud client JSON-serializes non-FormData bodies (a gzip `Uint8Array` becomes `{"0":31,…}`) and posts raw bytes straight to the host with its own `Bearer` + `X-Org-Id` (:634–660).
- Git-sync paths are literal strings, deliberately NOT routed through the remappable endpoint manifest — adding keys there would break already-published manifests (:678–682).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "automation service api dispatch trigger", limit: 10, fields: ["signature", "lines", "docstring"] });
// → AutomationService.dispatchAutomation :428-443, buildPinnedCloudHeaders :219-223, …
await mcp.codebase_memory.trace_path({ project: "openhands", function_name: "callCloudProxy", direction: "both", depth: 2 });
// → 48 callers across 12+ service classes confirm this is THE transport split hub
```

## Verdict
Adopt the call-time backend resolution + explicit-pin escape hatch and the placeholder-trigger/compensating-delete import transaction. Adapt the axios-vs-proxy split to your host's transports (any pair of "direct SDK" vs "gateway" clients works). Omit the OpenHands-specific endpoint manifests, telemetry distinct-id header, and cloud org-id semantics. Coverage caveat: none recorded at pin (`no_recorded_issue`); vitest runner unavailable in the inspo tree, so test evidence is read-at-HEAD, not executed.
