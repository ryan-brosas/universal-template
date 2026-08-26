<!-- capsule-v2 -->
# Provider priority ranking — how do you break ties when several providers serve the same model?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Given `gpt-5.5` on OpenAI, OpenRouter, and a gateway, which provider should automatic selection pick?

## Config-first rank map with a curated default tail
**Path/Symbol:** `packages/catalog/src/identity/priority.ts:DEFAULT_MODEL_PROVIDER_ORDER` (:14), `buildModelProviderPriorityRank` (:50).
**Signature:** `buildModelProviderPriorityRank(configuredProviderOrder?: readonly string[]): Map<string, number>`.
**Data Shape:** three curated bands: first-party/native accounts (openai-codex, anthropic, google*, kimi/moonshot, qwen, zai, xai, mistral, deepseek, groq) → high-quality aggregators (fireworks, cerebras, baseten, openrouter, aimlapi, together) → generic gateways/editor proxies (opencode-zen, gitlab-duo, kilo, vercel/cloudflare ai-gateway, nanogpt, github-copilot).

### Decisive source
```ts
function addProviderRank(rank: Map<string, number>, provider: string): void {
  const normalized = provider.trim().toLowerCase();
  // First configured entry wins its rank; duplicates and blanks skipped.
  if (!normalized || rank.has(normalized)) return;
  rank.set(normalized, rank.size);
}
// User config occupies the LOW ranks (wins); defaults fill in AFTER so an
// explicitly-configured relay can outrank first-party if the operator wants.
```

**Flow:** build once at selection time → configured order ranks first → default order appends → lookup compares `rank.get(a) ?? Infinity`.
**Invariant:** (1) generic gateways "are useful when picked explicitly but should not win ambiguous automatic role selection" — that policy is encoded purely in band ORDER; (2) normalization is trim+lowercase; (3) unknown providers rank last rather than throwing.
**Probe:** coverage caveat: no dedicated unit file pins the ordering; contract is structural (band comments + insertion-order semantics) — deterministic by construction. Nearest consumer tests live in coding-agent selection suites outside this package.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "DEFAULT_MODEL_PROVIDER_ORDER buildModelProviderPriorityRank", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt config-then-defaults rank maps for same-model tie-breaks; re-curate the bands to your ecosystem; omit if you never auto-select providers. Coverage caveat recorded above.
