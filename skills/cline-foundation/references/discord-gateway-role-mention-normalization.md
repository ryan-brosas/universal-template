<!-- capsule-v2 -->
# Discord gateway role-mention normalization — how do you restore role-mention semantics on events forwarded from a WebSocket gateway before the interactions adapter sees them?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When gateway events are forwarded to the interactions webhook, Discord does not set `is_mention` for role mentions — how do you reconstruct that flag without trusting a stale role cache?

## Pre-adapter request rewrite with promise-cached, self-healing role lookup
**Path/Symbol:** `apps/cli/src/connectors/adapters/discord.ts:normalizeDiscordForwardedGatewayRequest` (:338-384) + `readDiscordBotGuildRoleIds` (:311-336).
**Signature:** `normalizeDiscordForwardedGatewayRequest(input: { request: Request; botToken: string; applicationId: string }): Promise<Request>`.
**Data Shape:** In: the raw forwarded POST, bot token, application id. Out: the SAME Request untouched (non-gateway events, already-`is_mention` events, no role mentions, no role intersection) or a NEW Request with `data.is_mention: true` merged into the JSON body.

### Decisive source
```ts
const cached = botGuildRoleCache.get(cacheKey);
if (cached) return cached;
const pending = fetchDiscordJson({ ... }).then(
    (value) => new Set(readStringArray((value as DiscordGuildMemberResponse).roles)),
    () => {
        botGuildRoleCache.delete(cacheKey);   // self-heal: next event retries
        return new Set<string>();
    },
);
botGuildRoleCache.set(cacheKey, pending);
return pending;
```

**Flow:** parse the event from a CLONED request (request bodies are single-read) → only `GATEWAY_MESSAGE_CREATE` proceeds → skip if `is_mention === true` already, if `mention_roles` is empty, or if `guild_id` is missing → fetch the bot's own guild member record (`/guilds/{guild}/members/{applicationId}`) and intersect its role set with `mention_roles` → on intersection, rebuild the Request with new Headers and `is_mention: true` in the body → hand the normalized request to `discord.handleWebhook`.
**Invariant:** (1) The role cache stores the PROMISE, not the resolved value — concurrent events for one guild share a single fetch. (2) A failed lookup deletes its cache entry before returning an empty set, so the NEXT event retries instead of caching the failure forever. (3) The original Request is returned unchanged on every non-rewriting path — the adapter's signature verification still sees the original bytes.
**Probe:** `apps/cli/src/connectors/adapters/discord.test.ts` — "normalizes forwarded bot-role mentions as Discord mentions" (member endpoint queried, `is_mention` becomes true) and "retries bot role lookups after transient Discord API failures" (500 then 200 ⇒ first event NOT rewritten, second rewritten, fetch called exactly 2 times).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/discord.ts", symbol: "normalizeDiscordForwardedGatewayRequest" });
```

## Verdict
Adopt the pattern: promise-keyed cache with delete-on-failure for any per-entity remote lookup feeding a hot event path, and clone-before-parse when inspecting a Request you must forward. Adapt the Discord member endpoint and `is_mention` flag to the platform. Omit the gateway-forwarding transport itself (deployment-specific). Coverage caveat: fully test-pinned including the transient-failure retry.
