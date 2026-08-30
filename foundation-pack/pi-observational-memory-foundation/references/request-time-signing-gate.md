<!-- capsule-v2 -->
# Request-time-signing gate — empty auth payload ≠ unauthenticated when the provider signs its own requests

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When your pre-flight auth gate sees a resolved-but-empty credential (no apiKey, no headers), how do you tell "ambient/request-time-signed provider — proceed" from "not logged in — fail" without silently disabling the whole feature?

## Path/Symbol
**Path:** `src/runtime.ts`
**Symbol:** `resolveModel` decision ladder **:126-220** (acceptance predicate `:183-188`); helpers `hasUsableAuth` **:20-23**, `countUsableHeaders` **:31-36**, `hasConfiguredProviderCredential` **:79-85**.

**Signature:**
```ts
type ResolveResult =
  | { ok: true; model: unknown; apiKey?: string; headers?: Record<string,string>; env?: Record<string,string>; baseUrl?: string }
  | { ok: false; reason: string };
function hasUsableAuth(auth: { apiKey?: unknown; headers?: unknown }): boolean   // non-empty string key OR ≥1 non-empty string header value
```

**Data Shape:** host facade returns `getApiKeyAndHeaders(model) → { ok: boolean, apiKey?, headers?, env?, baseUrl? }`. The trap shape is `{ ok: true, apiKey: undefined, headers: undefined }` — measured on pi 0.84.2 with `AWS_PROFILE`: `checkAuth("amazon-bedrock") → { source: "AWS_PROFILE", type: "api_key" }`, `hasConfiguredAuth → true`, yet `getApiKeyAndHeaders → { ok: true, apiKey: undefined, headers: undefined }` because `bedrockAuth.resolve()` returns `{ auth: {}, source: "AWS_PROFILE" }` and the host signs SigV4 itself at request time. Google Vertex ADC resolves identically empty.

### Decisive source
```ts
const usable = hasUsableAuth(auth);
const resolvedEmptyApiKey = typeof auth.apiKey === "string" && auth.apiKey.length === 0;
let providerCredentialConfigured = hasConfiguredProviderCredential(ctx.modelRegistry, model);
if (auth.ok === true && !usable && !isOAuth && !resolvedEmptyApiKey && !providerCredentialConfigured) {
    providerCredentialConfigured = await this.recheckProviderCredential(...);   // second half of the host's own gate (see stale-snapshot-recheck)
}
const signsAtRequestTime =
    auth.ok === true && !isOAuth && !resolvedEmptyApiKey && providerCredentialConfigured;
if (!auth.ok || (!usable && !signsAtRequestTime)) {
    const reason = isOAuth
        ? `authentication failed for provider "${provider}" — OAuth credentials may have expired; run '/login ${provider}' to re-authenticate`
        : `no API key or auth headers for provider "${provider}"`;
    return { ok: false, reason };
}
```

**Flow:** configured-model lookup (`modelRegistry.find(provider,id)`, warn-and-fall-back-to-session-model on miss) → resolve auth → compute `usable` / `resolvedEmptyApiKey` / `isOAuth` / snapshot-half `providerCredentialConfigured` → ONLY if everything already looks ambient-shaped (ok:true, nothing usable, not OAuth, not an empty-string key, snapshot says unconfigured) spend the bounded live re-check → accept iff `usable || signsAtRequestTime`.

**Invariant (the porter trap):** An empty auth payload is THREE different states and only the provider-credential half separates them:
1. **Request-time signing (accept):** host reports a credential source (`hasConfiguredAuth === true`) but deliberately hands over nothing — it will sign the request itself. Treating this as "unauthenticated" aborted every consolidation silently — no error, no cost, no latency — on Bedrock/SSO and Vertex hosts (the exact bug this fixed).
2. **Expired OAuth (fail with `/login` reason):** `isUsingOAuth() === true` + empty resolution means the stored token no longer resolves. Never re-checked.
3. **Misconfiguration (fail plainly):** a credential that resolved to an empty *string* key (`apiKey: ""`) is a broken config, not ambient auth — `resolvedEmptyApiKey` keeps it failing even though `hasConfiguredAuth` is true.
The blunt fix ("accept any ok:true with nothing to carry") let case 3 AND fully-unauthenticated providers through — the test pins `[false, undefined]` `hasConfiguredAuth` both rejecting. `hasConfiguredProviderCredential` is defensive duck-typing (`?.(model) === true`, try/catch → false): an unknown answer must never read as "authenticated".

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "signsAtRequestTime" src/runtime.ts          # expect 3 && \
grep -n "hasConfiguredProviderCredential(" src/runtime.ts | wc -l        # expect 3 (def :79; snapshot read :164 ctx.modelRegistry; re-read :271 registry) && \
npx vitest run tests/ambient-credential-auth.test.ts  # 12 passed (5 in the request-time-signed describe)
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "resolveModel hasUsableAuth hasConfiguredAuth signsAtRequestTime", limit: 5 });
// rank1: ...src.runtime.Runtime.resolveModel Method src/runtime.ts 126-220
```

**Verdict:** Adopt the three-state separation and the mirror-the-host rule ("our pre-flight must not be stricter than the host's own acceptance"). Adapt the facade method names to your host's registry surface. Omit nothing here — the negative tests are the specification.
