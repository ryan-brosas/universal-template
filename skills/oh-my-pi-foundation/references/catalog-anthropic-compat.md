<!-- capsule-v2 -->
# Anthropic compat detection — which endpoints sign thinking blocks, and what breaks when you guess wrong?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you decide per model whether unsigned thinking may be replayed, tool choice forced, or sampling params sent?

## Build-once ResolvedAnthropicCompat from URL markers + id classification
**Path/Symbol:** `packages/catalog/src/compat/anthropic.ts:isOfficialAnthropicApiUrl` (:26), signing-proxy marker set (:60–103), `isAnthropicSigningProxyUrl` (:105), `buildAnthropicCompat` (:117).
**Signature:** `buildAnthropicCompat(spec: ModelSpec<"anthropic-messages">): ResolvedAnthropicCompat` — runs exactly once per model; request handlers read fields only.
**Data Shape:** flags incl. `{officialEndpoint, signingEndpoint, supportsEagerToolInputStreaming, supportsLongCacheRetention, supportsMidConversationSystem, supportsForcedToolChoice, supportsSamplingParams, requiresToolResultId, requiresThinkingEnabled, replayUnsignedThinking, escapeBuiltinToolNames, streamIdleTimeoutMs}`.

### Decisive source
```ts
// The ONE auth-sensitive host check: OAuth credentials attach based on it,
// so it requires the exact origin or a path boundary — a bare prefix check
// would accept lookalikes like https://api.anthropic.com.evil.com.
export function isOfficialAnthropicApiUrl(baseUrl?: string): boolean {
  if (!baseUrl) return true; // missing baseUrl is official ON PURPOSE
  const lower = baseUrl.toLowerCase();
  return lower === OFFICIAL_ANTHROPIC_URL || lower.startsWith(`${OFFICIAL_ANTHROPIC_URL}/`);
}

// Signing endpoints enforce signature-based thinking-chain integrity, so
// unsigned thinking must stay TEXT there. Every other reasoning endpoint
// replays unsigned thinking natively so the chain survives continuation —
// otherwise next tool-call arguments destabilize (#2005 #2257 #2265 …).
replayUnsignedThinking: !signingEndpoint && (Boolean(spec.reasoning) || modelMatchesHost(spec, "deepseekFamily")),
```

**Flow:** detect official (exact-host) → detect signing proxies by URL MARKER regexes (Cloudflare `/anthropic` gateway route, Vertex `publishers/anthropic/`, Bedrock `bedrock-runtime.<region>.amazonaws.com`, Azure `<res>.(inference|services).ai.azure.com`) plus provider-id hosts (Copilot, ZenMux) → Kimi K2.7-Code/K3 on native Moonshot hosts get `requiresThinkingEnabled` + downgraded forced choice (server keeps thinking on; `tool_choice 'specified'` 400s against it) → Opus 4.7+/Fable sampling restrictions via identity predicate → Z.AI deserializer quirk forces `requiresToolResultId` → sparse user overrides applied last (`applyCompatOverrides`: defined values only, unknown keys ignored).
**Invariant:** (1) runtime re-checks `isAnthropicSigningProxyUrl` with the EFFECTIVE url because compat goes stale after Foundry/base-url reroutes; (2) long cache retention is official-only unless a proxy opts in explicitly; (3) mid-conversation system requires official host AND a capable model id (Bedrock/Vertex reject the role); (4) custom signing proxies are the user's responsibility — the transport surfaces a pointed remediation on first signing 400 (#4297).
**Probe:** direct `packages/catalog/test/build.test.ts:1386–1398` (missing-baseUrl-official / https / non-https / LOOKALIKE rejection); issue repro `test/issue-2558-repro.test.ts` (Copilot eager streaming), `issue-4297-repro.test.ts` (unsigned-thinking remediation).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildAnthropicCompat isAnthropicSigningProxyUrl replayUnsignedThinking", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the exact-origin auth gate, the marker-based signing-proxy set, and override-after-detection ordering; adapt the proxy list as new gateways appear; omit Bedrock/Azure markers if you don't front those. Coverage caveat: none.
