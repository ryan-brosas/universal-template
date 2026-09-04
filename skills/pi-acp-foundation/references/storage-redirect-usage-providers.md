<!-- capsule-v2 -->
# Session-map redirect + usage/provider surface — where does adapter state live, and what new UNSTABLE read APIs does the client get?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you make adapter-owned storage testable via env redirect, and how are pi's model stats projected onto ACP's unstable provider/usage shapes?

## PI_ACP_SESSION_MAP override + sessionStatsToAcpUsage + piModelsToProviderInfo
**Path/Symbol:** `src/acp/paths.ts` (`getPiAcpSessionMapPath` :13-18) + `src/acp/usage.ts` whole file + `src/acp/providers.ts` whole file.
**Signature:** `export function getPiAcpSessionMapPath(): string`; `export function sessionStatsToAcpUsage(stats: unknown): Usage | null`; `export function piModelsToProviderInfo(models: Array<Record<string, unknown>>): ProviderInfo[]`.
**Data Shape:** usage gate — returns null when `totalTokens <= 0 && inputTokens <= 0 && outputTokens <= 0` so callers OMIT the field instead of emitting zeros; non-finite numbers coerce to undefined; missing `total` derives as input+output; cost rides `_meta.piAcp.cost`. Providers: KNOWN_PROTOCOLS map (`anthropic, openai, openrouter→openai, azure, vertex, bedrock`), unknown provider → sentinel protocol `` `_${provider}` ``; one entry per distinct provider id (first model wins), `required: false`, baseUrl passed through when string.

### Decisive source
```ts
const totalTokens = num(tokens.total) ?? inputTokens + outputTokens
if (totalTokens <= 0 && inputTokens <= 0 && outputTokens <= 0) return null
```
```ts
const apiType: LlmProtocol = KNOWN_PROTOCOLS[provider.toLowerCase()] ?? `_${provider}`
```

**Flow:** session map path resolution checks `PI_ACP_SESSION_MAP` FIRST and `resolve()`s it (F-027: the smoke matrix redirects storage away from the user store; every store consumer goes through this single function). Usage is collected post-turn by the agent under a 2.5s timeout race and attached to PromptResponse. Provider listing spawns an ephemeral pi subprocess at last-known cwd, calls `get_available_models`, projects to ProviderInfo[], disposes in `finally`.
**Invariant:** all adapter-owned paths funnel through `paths.ts` helpers (no scattered `~/.pi/pi-acp` literals); "no usable token numbers" ⇒ null ⇒ omitted field, never fabricated zeros; unknown protocols keep a round-trippable `_name` sentinel rather than dropping the provider.
**Probe:** `npx tsx --test test/unit/paths.test.ts test/unit/session-usage.test.ts test/unit/providers.test.ts` (override + zero/null matrices + protocol mapping) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "sessionStatsToAcpUsage piModelsToProviderInfo getPiAcpSessionMapPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt env-redirected storage roots for testability, null-means-omit usage projection, and sentinel-protocol provider mapping. Adapt the env name and stats payload keys to your backend. Omit provider listing if your client has no unstable providers capability. Direct tests executed green at pin.
