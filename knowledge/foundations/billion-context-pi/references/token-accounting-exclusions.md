<!-- capsule-v2 -->
# Token accounting exclusions — which messages must a context-usage estimate skip to agree with what the provider will actually charge?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** When the host cannot supply a real usage number, which messages does the fallback estimator exclude so compression decisions are not made on inflated counts?

## estimateTokens: skip compress tool calls + already-covered ids
**Path/Symbol:** `src/tokens.ts`: `estimateTokens` (:12-20), `collectCoveredMessageIds` (:3-10), `lastUserMessageId` (:24-30); consumed in `src/index.ts` `wireContextTransform` (:109-117).
**Signature:** `collectCoveredMessageIds({blocks:[{active,effectiveMessageIds}]}) -> Set<string>`; `estimateTokens(messages: CoreMessage[], coveredIds?) -> number`; `lastUserMessageId(entries) -> string | undefined`.
**Data Shape:** covered = union of `effectiveMessageIds` over ACTIVE blocks only (inactive blocks' messages count again — decompression restores them to live cost); estimate delegates per-message to the kernel's `defaultCountTokens`.

### Decisive source
```ts
// src/tokens.ts:14-17 — two exclusions that keep the estimate honest
for (const m of messages) {
  if (m.toolName === "compress") continue;   // meta-chatter, not content
  if (coveredIds?.has(m.id)) continue;       // summarized inside a block already
  tokens += defaultCountTokens(m.text ?? "");
}
```

**Flow:** every turn the transform spine computes BOTH numbers: `realUsage = ctx.getContextUsage()` (preferred — includes system prompt + tool schemas and matches the footer) and `estimated = estimateTokens(coreMessages, coveredIds)`; `tokenCount = real > 0 ? real : estimated` feeds the kernel's nudge/compress decisions (:115-117). The kernel counter is CJK-aware (each CJK char = 1 token; non-CJK chars/4) — naive chars/4 undercounts Chinese text 4×. The same module owns `lastUserMessageId`: reverse scan for role==="user" giving the per-turn dedup key used by nudge gating.
**Invariant:** (1) compress tool calls are excluded from token estimates — counting them inflates usage exactly when the model is being asked to compress; (2) only ACTIVE blocks' members are covered — after decompression their ids leave the set so they count as live tokens again; (3) the real-usage preference is load-bearing: estimates exist solely as a fallback for hosts with no usage API, never to override it.
**Probe:** `tests/tokens.test.ts:5` (kernel-consistent counting), `:21` ("skips compress tool calls"), `:31` ("skips covered (already-compressed) message ids" — covered set excludes inactive blocks by construction), `:41-69` (lastUserMessageId ladder incl. entries without message field).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "estimateTokens lastUserMessageId collectCoveredMessageIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two exclusions plus active-block-only coverage for any usage estimator feeding compression policy. Adapt the counter itself to your kernel. Omit the real-vs-estimated split only if your host guarantees a usage number on every call.
