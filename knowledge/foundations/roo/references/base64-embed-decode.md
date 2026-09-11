<!-- capsule-v2 -->
# base64 embedding decode — why does every SDK-backed embedder request base64 encoding?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How do the openai-compatible and openrouter embedders avoid silently truncated embeddings?

## Bypass the OpenAI SDK's float-array parser
**Path/Symbol:** `src/services/code-index/embedders/openai-compatible.ts:_embedBatchWithRetries` (:273-297); same in `openrouter.ts` (:196, :213-226).
**Signature:** `encoding_format: "base64"` on `embeddings.create(...)`; response items typed `embedding: string | number[]`.
**Data Shape:** base64 string → `Buffer.from(b64)` → `Float32Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / 4)` → `Array.from(float32)`.

### Decisive source
```ts
// OpenAI package (as of v4.78.1) has a parsing issue that truncates embedding dimensions to 256
// when processing numeric arrays ... By requesting base64 encoding, we bypass the package's parser
encoding_format: "base64",
...
const float32Array = new Float32Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / 4)
```

**Flow:** request carries base64 → SDK hands back an opaque string → code decodes as little-endian float32 → plain number[] for Qdrant. Non-string embeddings (already arrays) pass through untouched, so endpoints ignoring the format still work. The direct-fetch branch (full endpoint URLs like Azure `/deployments/.../embeddings`) also sets `api-key` AND `Authorization` headers simultaneously for Azure/OpenAI compatibility.
**Invariant:** if you swap to native JSON arrays you inherit the dimension-truncation bug for >256-dim models (1536/3072-dim profiles would ALL break); if you keep base64, byteLength MUST be divisible by 4 — a malformed body yields garbage dims rather than an error.
**Probe:** `src/services/code-index/embedders/__tests__/openai-compatible.spec.ts`; executed pins: comment line + `encoding_format: "base64"` in both files.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "encoding_format base64 Float32Array makeDirectEmbeddingRequest", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt base64+manual float32 decode wherever an SDK parses embedding arrays. Adapt header strategy per gateway. Omit Azure URL-pattern detection (`isFullEndpointUrl`) unless porting multi-endpoint config.
