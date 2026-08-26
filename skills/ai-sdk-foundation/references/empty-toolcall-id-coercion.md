<!-- capsule-v2 -->
# Empty-string tool-call-id coercion — why must id fallback use `||` not `??`?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Providers emit tool calls with `id: ""` — why did every affected adapter change from nullish coalescing to falsy coalescing?

## Falsy-coalesce id ladder
**Path/Symbol:** decisive instance `packages/google/src/google-language-model.ts:879`; identical twins `groq-chat-language-model.ts:244`, `alibaba-chat-language-model.ts:222`, `amazon-bedrock-chat-language-model.ts:606` (`part.toolUse?.toolUseId || this.config.generateId()`).
**Signature:** `const toolCallId = part.toolCall.id || generateId();`
**Data Shape:** wire ids are optional strings; downstream consumers key maps by them.

### Decisive source
```ts
- toolCallId: toolCall.id ?? generateId(),
+ const toolCallId = part.toolCall.id || generateId();
```

**Flow:** `??` only catches `null`/`undefined`, so `""` passed through as a REAL id; empty-string keys then collide in any multi-call turn (every id-less call shares one key), corrupting result correlation and history round-trips. Falsy coalescing routes `""`, `null`, AND `undefined` to the generator.
**Invariant:** A missing-or-empty provider id must ALWAYS yield a fresh generated id — treat empty string as absent for identity purposes.
**Probe:** deterministic probe: `grep -cF "toolCall.id || generateId()" packages/groq/src/groq-chat-language-model.ts` → `1`. Direct tests: `google-language-model.test.ts` ("should generate an ID when toolUseId is empty" class suites across adapters).
**Retrieve:** verified live @9d9a73f — grep census above; graph anchors on each adapter's doGenerate/doStream.

## Verdict
Adopt `||` semantics for ALL provider-assigned identifiers used as map keys; adapt the generator injection point; census shows the same one-line fix landing in ≥5 provider packages — port it as a family rule, not per-provider.
