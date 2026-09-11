<!-- capsule-v2 -->
# Catalog family predicates — how do you gate wire behavior on model family when any proxy can serve any model?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you decide "is this id a member of family X" such that a Kimi keeps its quirks behind OpenRouter, Kilo, or a custom gateway?

## Namespace-agnostic predicates over id OR display name, memoized process-lifetime
**Path/Symbol:** `packages/catalog/src/identity/family.ts:memo` (:22), `isKimiModelId` (:35), `isClaudeModelId` (:62), `isOpenAIWireGen54Plus` (:232), `isOpenAISamplingRestrictedModelId` (:281), `modelFamilyToken` (:351), `findThinkingVariantToken` (:452), `stripThinkingVariantToken` (:472).
**Signature:** `memo<T>(fn: (modelId: string) => T): (modelId: string) => T`; predicates `(modelId: string) => boolean`; `findThinkingVariantToken(modelId): {index,length} | undefined`.
**Data Shape:** unbounded Map memo (ids are a bounded set in practice); predicates mix three match styles: boundary-guarded prefix regex (`/(^|\/)kimi[-.]/i`), substring-on-name (`deepseek` — proxies rename ids but keep display names), and parsed-version floors.

### Decisive source
```ts
// Version FLOOR, not an allowlist, so 5.6/6.x inherit support automatically.
const isOpenAIWireGen54Plus = memo((modelId: string): boolean => {
  const parsed = parseOpenAIModel(bareModelId(modelId));
  if (!parsed) return false;
  return semverGte(parsed.version, "5.4");
});
// Two features share one floor: earlier ids reject with
// "Unsupported value: 'all_turns'…" / "Unsupported parameter: 'reasoning.summary'…"
export const supportsAllTurnsReasoningContext = isOpenAIWireGen54Plus;
export const supportsCodexReasoningSummary = isOpenAIWireGen54Plus;

// Negated forms name the NON-thinking SKU — never match them.
const THINKING_VARIANT_TOKEN_RE = /-(?:thinking|reasoner|reasoning)(?=$|[^a-z0-9])/gi;
```

**Flow:** call sites gate wire fields through predicates instead of `provider ===` checks → predicate normalizes namespace (`bareModelId`, dotted Bedrock profiles `us.anthropic.claude-*` handled by `(^|[/.])claude[-.]`) → version-capable families compare parsed SemVer against floors → `modelFamilyToken` folds everything onto ONE coarse vendor token (comparison-only, explicitly NOT stable to persist) for cross-family reviewer picking; `preferredDialect` maps token → chat template dialect with `"xml"` fallback.
**Invariant:** (1) floors beat allowlists — new generations must inherit behavior without code changes; (2) Grok effort capability IS an allowlist (`GROK_EFFORT_CAPABLE_PREFIXES`) because other Grok reasoners think natively but 400 on the param — use allowlists only when rejection is proven; (3) thinking-variant tokens end at any non-alphanumeric and skip `non-`/`no-` prefixes; (4) sampling restrictions span o-series AND gpt-5+ on EVERY host (issue #5606) because even chat variants reject temperature.
**Probe:** direct `packages/catalog/test/identity-family.test.ts:391` (`isGrokReasoningEffortCapable`), `:411` (multi-agent xhigh-as-agent-count), `:426` (xhigh capable), `:184/:236` (MiniMax M2 dotless aliases, MuseSpark), `:277` (`isOpenAIModelId`), `:329` (`modelFamilyToken`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "isKimiModelId modelFamilyToken supportsHashlineEdits family predicate", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the three-tier predicate design (boundary regex / name substring / version floor) with process-lifetime memoization and the coarse family token for comparisons; adapt the specific SKU lists (they track vendor releases by design); omit hashline-edit support gating if your host has no line-anchored edit format. Coverage caveat: none — this is the most heavily unit-tested file in the package.
