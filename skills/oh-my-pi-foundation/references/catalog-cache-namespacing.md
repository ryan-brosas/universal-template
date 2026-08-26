<!-- capsule-v2 -->
# Credential-scoped cache namespaces — when must a provider's model cache be partitioned by credential?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you stop account B from loading account A's authoritative discovery cache at startup?

## Namespace keys hash credential + endpoint + workspace scope
**Path/Symbol:** `packages/catalog/src/provider-models/cache-provider-id.ts:resolveModelCacheProviderId` (:52), `resolveOllamaModelCacheProviderId` (:37), `CREDENTIAL_SCOPED_MODEL_CACHE_PROVIDERS` (:8); `provider-models/special.ts:gitLabDuoWorkflowModelCacheProviderId` (:66), `unionCodexModels` (:75).
**Signature:** `resolveModelCacheProviderId(providerId, {apiKey?, baseUrl?}): string` — returns e.g. `` github-copilot:models-v1:<Bun.hash(token\0baseUrl).toString(36)> ``.
**Data Shape:** versioned namespace literals encode schema migrations (`cursor:max-mode-v3`, `opencode-*:models-v2`, `vllm:models-v2`, `litellm:rich-v6`) — bumping the literal invalidates every old row without a migration.

### Decisive source
```ts
// Copilot model specs bake in the PLAN-specific endpoint (personal vs
// Business/Enterprise) resolved from the credential. Keying the namespace on
// the credential means switching COPILOT_GITHUB_TOKEN misses the prior
// endpoint's cache and re-runs discovery instead of hitting the stale host
// and 403ing (PR #8510 review).
const scope = `${options.apiKey ?? ""}\u0000${baseUrl}`;
return `github-copilot:models-v1:${Bun.hash(scope).toString(36)}`;

// GitLab Duo discovery is namespace-specific AND cwd-driven (git remote
// auto-discovery): two workspaces sharing one token must not share a cache.
const scope = [config.baseUrl ?? "", namespaceId, projectId, cwd].join("\u0000");
return `gitlab-duo-agent:${Bun.hash(`${apiKey}\u0000${scope}`).toString(36)}`;

// Codex multi-account: union per-account catalogs; ANY fetch failure returns
// null so a partial list can't replace the authoritative catalog (#6265).
for (const result of results) { if (!result) return null; }
```

**Flow:** model-manager options call the resolver before constructing options → default branch returns bare provider id → Ollama normalizes any user baseUrl back to its origin+native-path form so custom paths share the default endpoint's cache → malformed URLs fall back to default scope (discovery will also fall back) → hashed with Bun.hash base36 for a compact SQLite key.
**Invariant:** (1) cache-namespace version bumps are the migration mechanism — each carries a comment naming the stale rows it orphans; (2) authoritative caches MUST be scoped to everything that determines their content (credential, resolved endpoint, namespace config, env, effective cwd); (3) hashing is non-reversible — tokens never appear in the DB; (4) partial multi-account discovery fails CLOSED.
**Probe:** direct `packages/catalog/test/provider-cache-id.test.ts:7/:24` (resolution contract); `test/github-copilot-model-limits.test.ts:107` ("does not reuse another token's authoritative cache after COPILOT_GITHUB_TOKEN switches"), `:155/:169` (structured OAuth key unwrap routes enterprise/business discovery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveModelCacheProviderId cacheProviderId credential scoped", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt credential/endpoint-scoped namespaces for any provider whose catalog depends on auth, and versioned namespace literals as invalidation; adapt the scope tuples to your providers; omit Ollama normalization if you have no local-endpoint provider. Coverage caveat: none.
