<!-- capsule-v2 -->
# gen_ai SemConv formatter — mapping AI SDK messages/finish-reasons onto OpenTelemetry GenAI semantic conventions

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How do provider-specific prompts/completions become standard `gen_ai.*` attribute payloads an observability backend can parse?

## Path/Symbol
`packages/otel/src/gen-ai-format-messages.ts` — `mapProviderName` (:76–109), `mapOperationName` (:114–125), `formatSystemInstructions` (:132–145), `convertMessagePartToSemConv` (:147–270), `getModality` (:272–278), `formatInputMessages` (:284–298), `formatModelMessages` (:304–333), `formatOutputMessages` (:553–628), `formatObjectOutputMessages` (:633–647), `mapFinishReason` (:649–660).

**Signature:** formators are pure functions over `LanguageModelV4Prompt` / `ModelMessage[]` returning JSON-ready `SemConvInputMessage[]` / `SemConvOutputMessage[]`; callers stringify via `{ input: () => JSON.stringify(...) }`.

**Data Shape:** SemConv parts are a discriminated union: `{type:'text'|'reasoning', content}`, `{type:'tool_call', id, name, arguments?}`, `{type:'tool_call_response', id, response}`, `{type:'blob', modality, mime_type, content}` vs `{type:'uri', …, uri}` for by-reference media, plus passthrough `{type: String(part.type)}` for unknown kinds. Output messages append a REQUIRED `finish_reason` per message.

### Decisive source
```ts
  const wellKnownPrefixes: Array<[string, string]> = [
    ['google.vertex', 'gcp.vertex_ai'],
    ['google.generative-ai', 'gcp.gemini'],
    ['google-vertex', 'gcp.vertex_ai'],
    ['amazon-bedrock', 'aws.bedrock'],
    ['azure-openai', 'azure.ai.openai'],
    ...
  ];

  for (const [prefix, mapped] of wellKnownPrefixes) {
    if (
      lower === prefix ||
      lower.startsWith(prefix + '.') ||
      lower.startsWith(prefix + '-')
    ) {
      return mapped;
    }
  }
```
(:79–106; comment :72–74 documents longest-prefix-first ordering so `google.vertex.chat` hits before bare `google`)

**Flow:** provider strings like `anthropic.messages` lowercase then match prefix OR `prefix.` OR `prefix-` boundaries → canonical ids (`gcp.gemini`, `aws.bedrock`, `x_ai`, `mistral_ai`); unmatched pass through UNCHANGED (unknown providers keep their identity, test :81). Operations collapse to `invoke_agent` for all four text/object ops (:116–119), `embeddings`, `rerank`, else passthrough. Finish reasons: `'tool-calls' → 'tool_call'` and crucially `other|unknown → 'stop'` (:656–657) — the SDK's vague reasons normalize to stop rather than leaking. File parts unwrap the data envelope (`{type:'data'|'url'|…}`) THEN branch: http(s)-prefixed strings and URL objects become `uri` parts; Uint8Array base64s into `blob`; unknown mediaType defaults modality `image` (:273). Tool results map output envelopes — `text/error-text/json/error-json → value`, `execution-denied → {denied:true, reason}` (:173–174, 3 sites), raw otherwise.

**Invariant:** (1) Order preservation is contractual — system messages stay INLINE in prompt order (tests :198 "should preserve system messages in prompt order", :690 same for ModelMessages), not hoisted; backends reconstruct conversations positionally. (2) `formatModelMessages` CONCATENATES prompt-string/array then messages array (:311–331) because generateText can carry both a prompt and history. (3) Unknown part types must not throw — they degrade to `{type:'<raw>'}` so one exotic part never kills a trace. (4) The exhaustive-switch `never` check (:265–268) is compile-time insurance that new V4 part types get explicit SemConv mappings.

**Probe:** `grep -c "wellKnownPrefixes" packages/otel/src/gen-ai-format-messages.ts` → 2. `grep -n "'ai.generateText': 'invoke_agent'" packages/otel/src/gen-ai-format-messages.ts` → :116. `grep -n "other: 'stop'" packages/otel/src/gen-ai-format-messages.ts` → :656. `grep -c "execution-denied" packages/otel/src/gen-ai-format-messages.ts` → 3. Direct tests: `gen-ai-format-messages.test.ts` ×35 its — provider matrix (:14–86 incl. `google-vertex`→`gcp.vertex_ai`, azure split :69–79), operation mapping (:88–134), blob-vs-uri (:306/:336), finish-reason table (:582–598), empty-input `[]` (:797).

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "mapProviderName wellKnownPrefixes gcp.vertex_ai", limit: 3 });
// → packages/otel/src/gen-ai-format-messages.mapProviderName Function 76-109
```

**Verdict:** ADOPT whole — this file IS the SemConv translation table for GenAI tracing.
