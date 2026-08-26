<!-- capsule-v2 -->
# Copilot wire metadata — how do enterprise endpoints, API-version headers, and key envelopes decompose?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you route Copilot discovery/chat to personal vs Business vs Enterprise hosts from one credential?

## Envelope-parsing keys + plan-endpoint probe + versioned capi headers
**Path/Symbol:** `packages/catalog/src/wire/github-copilot.ts:COPILOT_API_VERSION` (:25), `COPILOT_API_HEADERS` (:30), `discoverGitHubCopilotApiEndpoint` (:84), `parseGitHubCopilotApiKey` (:108), `getGitHubCopilotBaseUrl` (:140).
**Signature:** `parseGitHubCopilotApiKey(raw): {accessToken, enterpriseUrl?, apiEndpoint?}`; `discoverGitHubCopilotApiEndpoint(token, fetch, signal?): Promise<string | undefined>`.
**Data Shape:** API-key envelope = JSON `{token, enterpriseUrl?, apiEndpoint?}`; raw strings pass through as bare tokens; enterprise hosts normalize to `copilot-api.<domain>`.

### Decisive source
```ts
// Newer versions unlock tiered context metadata: /models reports the full
// long-context window in capabilities.limits plus per-tier boundaries/prices.
// Without it: 264k instead of 1M for Claude Opus.
// NEVER send this to api.github.com REST endpoints — they validate
// X-GitHub-Api-Version against the REST vocabulary.
export const COPILOT_API_VERSION = "2026-06-01";

// Plan endpoint probe is BEST-EFFORT and bounded by the caller's signal — a
// stalled probe otherwise blocks discovery indefinitely. Public-host
// enterprise domains are rejected (they would loop back to REST).
```

**Flow:** credential arrives (raw or JSON envelope) → parse tolerantly (invalid JSON ⇒ treat whole string as token) → resolve effective base URL: explicit apiEndpoint > enterprise domain (`copilot-api.` prefix added when missing) > canonical personal host → optional `/copilot_internal/user` probe discovers the plan's advertised endpoint → all capi requests carry UA + version headers.
**Invariant:** (1) the version header belongs ONLY to api.githubcopilot.com traffic; (2) enterprise normalization strips public GitHub hosts and trailing slashes, requiring https; (3) endpoint discovery failure degrades to defaults rather than failing login.
**Probe:** direct `packages/catalog/test/github-copilot-model-limits.test.ts:82/:92` (plan-endpoint probe before discovery, fallback to personal), `:155/:169` (envelope unwrap routes enterprise/business discovery to the right host).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "parseGitHubCopilotApiKey discoverGitHubCopilotApiEndpoint COPILOT_API_VERSION", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt envelope parsing with raw-token fallback and the version-header host split; adapt the pinned version string as upstream tiers evolve; omit enterprise handling if you serve personal plans only. Coverage caveat: none.
