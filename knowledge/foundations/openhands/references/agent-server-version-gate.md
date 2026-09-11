<!-- capsule-v2 -->
# Agent-server bootstrap version gate — how does a UI refuse an incompatible backend without ever probing the wrong host?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** Where should frontend/backend compatibility be enforced, against which host, and how do you distinguish "too old" from "unknown version" from "unreachable"?

## Local-only probe with a three-way error taxonomy
**Path/Symbol:** `src/api/agent-server-compatibility.ts` (`loadAgentServerInfo` :320–400, `assertAgentServerVersionIsSupported` :293–318, `compareAgentServerVersions` :243–271, host-scoped cache :235–241).
**Signature:** `export async function loadAgentServerInfo(): Promise<AgentServerInfo | null>`; `compareAgentServerVersions(actual: string, required: string): 1 | -1 | 0 | null`.
**Data Shape:** Minimum version imported from static `config/defaults.json` (`defaults.compatibility.minimumAgentServer`). Errors: `AgentServerUnavailableError` (base; carries `noBackendConfigured`), `AgentServerUnsupportedVersionError` (code + actualVersion), `AgentServerUnknownVersionError` (code + nullable actualVersion).

### Decisive source
```ts
// The probe is a *local* agent-server concern — it verifies the runtime
// hosting the GUI is reachable. It must NEVER run against the active
// backend when that backend is cloud, because cloud hosts don't
// expose /api/server_info and would fail with a CORS error besides.
const local = getEffectiveLocalBackend();
```
```ts
if (parsedActual.prerelease && !parsedRequired.prerelease) return -1;
if (!parsedActual.prerelease && parsedRequired.prerelease) return 1;
```

**Flow:** resolve effective LOCAL backend → none? empty registry throws Unavailable(`noBackendConfigured:true`) so root.tsx shows manage-backends; cloud-active returns null (no probe) → `getServerInfo()` with 5 s timeout → 401 rethrown untouched (public-mode auth screen); other errors → Unavailable(details) → assert version → cache `{serverInfo, host}`.
**Invariant:** The three failure modes are distinct because their remedies differ: UnknownVersion ("restart/rebuild — /server_info gave nothing parseable"), UnsupportedVersion ("upgrade your backend"), Unavailable ("start it"). Version strings normalize through v-prefix strip, `+build` strip, `-prerelease` split; unparseable or literal `"unknown"` maps to UnknownVersion AND clears the cache. Prerelease sorts BEFORE release. The cache is host-scoped: `getCachedAgentServerVersion(host)` returns null when `host !== getEffectiveLocalBackend()?.host`.
**Probe:** `__tests__/api/agent-server-compatibility-bundled-pin.test.ts:98-140` — pins too-old (`1.27.1`) → UnsupportedVersionError with `requiredVersion`, missing version → UnknownVersionError with `actualVersion:null`, cloud-active never constructs ServerClient, empty registry rejects with AgentServerUnavailableError.

### Secondary invariants worth porting
- Public-mode key validation needs a SECOND, protected probe: `/server_info` is unprotected so a stale key still gets 200; only `SettingsClient.getSettings()` 401 proves rotation. Non-401 failures of that second probe are swallowed — the server IS up.
- Duck-typed error guards (`error.name === …` / `error.code === …`) work across SDK instance boundaries where `instanceof` can fail.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "agent server version compatibility compare cache", limit: 10, fields: ["signature", "lines"] });
// → compareAgentServerVersions :243-271, getCachedAgentServerVersion :235-241, loadAgentServerInfo :320-400
```

## Verdict
Adopt the local-vs-active probe split, the three-way taxonomy, hand-rolled semver-with-prerelease comparison, and host-scoped caching. Adapt the minimum-version source (defaults.json) and protected-endpoint choice to your product. Omit OpenHands' specific cloud/CORS rationale if you have no hybrid backend registry. Coverage caveat: none recorded at pin.
