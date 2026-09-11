<!-- capsule-v2 -->
# otel supplemental attributes + enrichSpan — the opt-in extension surface and its fail-open error contract

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How do you expose non-SemConv extras (usage details, providerMetadata, headers, runtime context) without breaking standard-conforming backends?

## Path/Symbol
`packages/otel/src/supplemental-attributes.ts` — option union (:9–17), `normalizeSupplementalAttributes` (:103–117), `getRuntimeContextAttributes` (:119–129) + recursive `addRuntimeContextAttribute` (:135–152), `getHeaderAttributes` (:154–162), `getDetailedUsageAttributes` (:164–181), `selectSupplementalAttributes` (:183–201). Consumer: open-telemetry.ts `getSpanAttributes` (:131–161).

**Signature:** 8 boolean toggles (`usage, providerMetadata, embedding, reranking, runtimeContext, headers, toolChoice, schema`) ALL default false; `selectSupplementalAttributes(telemetry, enabled, {option: AttributeSpecMap})` merges only enabled groups through selectAttributes.

**Data Shape:** namespaced attribute keys — `ai.settings.context.<flattened.path>`, `ai.request.headers.<Header>`, `ai.usage.inputTokenDetails.noCacheTokens`, `ai.usage.outputTokenDetails.{textTokens,reasoningTokens}`, `ai.response.providerMetadata`, plus per-family payload attrs (`ai.values`, `ai.documents`, `ai.ranking.type`, `ai.schema*`, `ai.prompt.toolChoice`, `ai.settings.output`).

### Decisive source
```ts
    try {
      customAttributes = this.enrichSpan?.({
        spanType,
        operationId,
        callId,
        runtimeContext,
      });
    } catch {
      customAttributes = undefined;
    }

    return {
      ...sanitizeAttributes(customAttributes),
      ...attributes,
    };
```
(open-telemetry.ts :146–160)

**Flow:** every span creation funnels through `getSpanAttributes`: run user's `enrichSpan({spanType, operationId, callId, runtimeContext})`, swallow ANY throw to undefined (fail-open), sanitize the custom bag, then spread STANDARD attributes OVER them — so a user key colliding with a gen_ai.* name loses. The test pins both halves: enrichment output visible on every span type (:1414–1481) and "ignores enrichment callback errors" (:1511–1531) where a throwing callback still yields the full standard attribute set. Runtime context flattens RECURSIVELY with dot-joined keys and preserves arrays as legal OTel arrays (:144–147 comment "Arrays are preserved because OTel supports primitive array attribute values"). Headers skip undefined values only.

**Invariant:** (1) Opt-in-by-default is the security/privacy stance — providerMetadata can contain account ids, headers can carry auth-adjacent metadata; nothing extra ships unless the integrator flips it. (2) Enrichment errors NEVER degrade tracing (catch-to-undefined), and enrichment cannot OVERRIDE SemConv keys because standard attributes win the spread — a porter reversing that order lets users corrupt operation names. (3) `gen_ai.operation.name` override ATTEMPTS in tests show up only when un-collided — the collision rule is the documented behavior. (4) Supplemental groups ride the SAME input/output gating as core attributes via selectAttributes.

**Probe:** `grep -n "'ai.settings.context.\${key}'" packages/otel/src/supplemental-attributes.ts` → :125. `grep -c "selectSupplementalAttributes(" packages/otel/src/open-telemetry.ts` → 18 call sites. Direct tests: open-telemetry.test.ts :1535/:1560 flat+nested context keys, :1585/:1739/:1840 enabled-only vs disabled emission; enrichSpan :1414/:1511.

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "supplementalAttributes normalizeSupplementalAttributes enrichSpan", limit: 3 });
// → otel normalizeSupplementalAttributes Function packages/otel/src/supplemental-attributes.ts 103-117
```

**Verdict:** ADOPT — reference design for safe, opt-in vendor extension of a standardized span.
