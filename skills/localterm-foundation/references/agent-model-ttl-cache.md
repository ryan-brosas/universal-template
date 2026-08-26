<!-- capsule-v2 -->
# Agent model-list TTL cache — how do you serve a CLI harness's slow model enumeration behind a daemon API without re-spawning it per request?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you cache an expensive subprocess-backed list (pi RPC `get_available_models`, ~1–5 s cold) so the first caller pays and later callers reuse — while still degrading when extensions crash headless?

## Module-level TTL memo + shim preference + empty-result retry
**Path/Symbol:** `packages/server/src/agent-models.ts:listAgentModels` (:98–108), `listModelsViaRpc` (:70–91), `listModelsViaRpcWith` (:14–68), `__resetAgentModelCache` (:112–114); route `packages/server/src/index.ts` GET `/agent-models` (:1962–1965).
**Signature:** `listAgentModels(shimsDir: string, piBinaryPath?: string): Promise<AgentModelInfo[]>`; internal `listModelsViaRpcWith(binary, pathEnv, extraFlags)` speaks NDJSON RPC.
**Data Shape:** `AgentModelInfo { id, name, provider, contextWindow?, reasoning? }` — optional fields spread ONLY when typeof matches; ids filtered non-empty; module state `{ at: number, models } | null` with `MODEL_CACHE_TTL_MS = 5 * 60 * 1000`.

### Decisive source
```ts
if (piBinaryPath) return listModelsViaRpcWith(piBinaryPath, process.env.PATH ?? "", []);
if (cachedModels && Date.now() - cachedModels.at < MODEL_CACHE_TTL_MS) return cachedModels.models;
let models = await listModelsViaRpc(shimsDir, []);
if (models.length === 0) models = await listModelsViaRpc(shimsDir, ["--no-extensions"]);
cachedModels = { at: Date.now(), models };
return models;
```
Why the shim binary is preferred over the real one:
```ts
// Prefer the localterm shim for the model list: it injects the pi-process
// secrets (so every provider with a key registers its models) then execs the
// real pi. The bare real pi has none of those keys, so most providers don't
// register and the list is nearly empty.
```
And the RPC read loop:
```ts
client.send({ type: "get_available_models", id: "models" });
let models: AgentModelInfo[] = [];
const deadline = Date.now() + 15_000;
while (Date.now() < deadline) {
  const line = await client.nextLine(Math.min(1000, deadline - Date.now()));
  if (line === null) {
    if (client.closed) break;
    continue;
  }
  let event: Record<string, unknown>;
  try { event = JSON.parse(line) as Record<string, unknown>; } catch { continue; }
  if (event.type === "response" && event.id === "models" && event.success) {
    ... map + filter ...
    break;
  }
}
client.close();
```

**Flow:** test override short-circuits shim+cache → TTL hit returns memoized list → spawn `pi --mode rpc --no-session` (prefer `<shimsDir>/pi` after stat+X_OK probe because only the shim carries provider-secret env), ask `get_available_models`, drain lines until the matching success response or a 15 s deadline → EMPTY result retries once with `--no-extensions` (extension-loaded pi can crash headless; built-ins still register) → result cached INCLUDING the empty case so a failing environment doesn't respawn pi per request.
**Invariant:** The cache stores outcomes, not successes — an empty list is a cached answer for 5 minutes, which bounds worst-case cost of a broken harness. Every field is coerced defensively (`String(...)`, conditional spread) so a shape drift upstream can't crash the daemon; unmatched/unparsable lines are skipped, never fatal.
**Probe:** `packages/server/tests/agent-runner.test.ts:394–435` (`listAgentModels` describe, integration tag) — fake-pi fixture emits the exact response envelope (:64–67); case 1 asserts the full mapped array incl. optional-field presence/absence (:408–420); case 2 clears PATH+SHELL and expects `[]` (:422–434); `beforeEach` calls `__resetAgentModelCache()` :398–399 proving cross-case isolation needs the reset. Executed this pass via `vp test -t "listAgentModels"`: 2 passed / 21 skipped.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "agent models cache reset", limit: 10 });
```
Executed live pre-write: rank#1 `__resetAgentModelCache` :112–114, rank#3 `listAgentModels` :98–108, rank#6 `listModelsViaRpc` :70–91, rank#7 `listModelsViaRpcWith` :14–68, plus client mirror `apps/terminal/src/utils/fetch-agent-models.ts` caches (:57–60) — all line-exact vs disk reads.

## Verdict
Adopt: module-level TTL memo of a subprocess-backed enumeration, shim-over-real binary preference for secret-dependent registration, empty→retry-without-extensions ladder, defensive wire mapping, exported reset hook for tests; adapt TTL to your harness's cold-start cost and the fallback flags to your extension system; omit the client-side mirror cache unless your UI also polls. Trap: caching only successful results — a dead harness would then respawn every poll; and reading RPC without an id filter would accept a stale response from a previous command.
