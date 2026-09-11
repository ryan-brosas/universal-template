<!-- capsule-v2 -->
# Gateway file-part base64 encoding — why does the transport MUTATE the prompt in place, and which part kinds are touched?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Where do binary file parts get encoded for JSON wire transport, and what does a porter get wrong about ownership?

## In-place Uint8Array → base64 sweep
**Path/Symbol:** `packages/gateway/src/gateway-language-model.ts:maybeEncodeFileParts` (199–220) + helper `maybeBase64EncodeFileData` (235–243).
**Signature:** `private maybeEncodeFileParts(options: LanguageModelV4CallOptions): LanguageModelV4CallOptions` (mutates and returns same object).
**Data Shape:** Walks `options.prompt[]`; for array-content messages touches: (a) parts with `type === 'file' | 'reasoning-file'`; (b) `tool-result` parts whose `output.type === 'content'`, iterating `output.value[]` for nested `file` entries. Only converts when `data.type === 'data'` AND `data.data instanceof Uint8Array` — URL/data-URL/string payloads pass untouched. Conversion is `{ ...data, data: Buffer.from(bytes).toString('base64') }`.

### Decisive source
```ts
for (const message of options.prompt) {
  if (!Array.isArray(message.content)) continue;   // string content skipped
  for (const part of message.content) {
    if (part.type === 'file' || part.type === 'reasoning-file') {
      part.data = maybeBase64EncodeFileData(part.data);   // in-place write-back
    } else if (part.type === 'tool-result' && part.output.type === 'content') {
      for (const contentPart of part.output.value) {
        if (contentPart.type === 'file') {
          contentPart.data = maybeBase64EncodeFileData(contentPart.data);
```

**Flow:** getArgs calls maybeEncodeFileParts BEFORE both doGenerate and doStream, so the SAME body-building path serves both; the returned `options` becomes the request `body` verbatim.
**Invariant:** The mutation is IN PLACE on the caller's prompt object — the AI SDK tolerates this because prompts are single-use per call, but a porter reusing a prompt object across retries after this point silently double-processes (harmless here only because Uint8Array→string is idempotent-guarded by instanceof). Missing the `reasoning-file` or tool-result-content cases drops binary attachments on the wire for exactly those part kinds.
**Probe:** `grep -cF 'part.data = maybeBase64EncodeFileData(part.data)' packages/gateway/src/gateway-language-model.ts` → `1`. Direct tests: gateway-language-model.test.ts 'Image part encoding' suites assert URL parts unmodified (:378 'should not modify image part with URL') and mixed content handled (:410).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayLanguageModel maybeEncodeFileParts base64", limit: 10 });
```
Resolves line-exact: `maybeEncodeFileParts Method gateway-language-model.ts 199-220`.

## Verdict
Adopt the exhaustive part-kind walk + instanceof guard; adapt `Buffer` to your runtime's base64 encoder (the repo's own provider-utils offers convertUint8ArrayToBase64); omit nothing — the two easily-missed part kinds ARE the reason this capsule exists. Coverage caveat: none.
