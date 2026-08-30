<!-- capsule-v2 -->
# UI chunk wire contract — which chunk shapes cross the SSE boundary, and why does the schema tolerate unknown FIELDS but not unknown TYPES?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the canonical server→client chunk envelope, and how do you version it so older clients and newer servers keep interoperating?

## uiMessageChunkSchema + UIMessageChunk
**Path/Symbol:** `packages/ai/src/ui-message-stream/ui-message-chunks.ts:uiMessageChunkSchema` (:23-215) + type `UIMessageChunk` (:226-398) + guard `isDataUIMessageChunk` (:400-404, prefix check only) + mapped type `DataUIMessageChunk` (:217-224).
**Signature:** 26-member discriminated union: text-start/-delta/-end, reasoning-start/-delta/-end, custom (`kind: \`${string}.${string}\``), error, tool-input-start/-delta/-available/-error, tool-approval-request/-response, tool-output-available/-error/-denied, source-url, source-document, file, reasoning-file, data-`${string}`, start-step, finish-step, start, finish, abort, message-metadata.

### Decisive source
```ts
export const uiMessageChunkSchema = lazySchema(() =>
  zodSchema<UIMessageChunk>(
    z.union([
      z.looseObject({ type: z.literal('text-start'), id: z.string(), ... }),
      // ...every member is a looseObject...
      z.looseObject({
        type: z.custom<`data-${string}`>(        // NOT a literal:
          value => typeof value === 'string' && value.startsWith('data-'),
          { message: 'Type must start with "data-"' },
        ),
        id: z.string().optional(), data: z.unknown(), transient: z.boolean().optional(),
      }),
      z.looseObject({ type: z.literal('finish'),
        finishReason: z.enum(['stop','length','content-filter','tool-calls','error','other']) }),
    ]),
  ),
);
```

**Flow:** every emitted chunk is validated against this union at the wire boundary; the reducer (client, pass 7/8) consumes exactly these members.
**Invariant:** (1) ALL members are `z.looseObject` — unknown extra fields from NEWER servers pass validation on OLDER clients (`ui-message-chunks.test.ts`:32 'accepts known chunks with fields added by newer servers'), but a `type` outside the union is REJECTED as TypeValidationError (:78 'rejects chunk types unknown to the client') — forward-compat lives in fields, never in types. (2) The `data-${string}` arm is a PREDICATE type with a startsWith('data-') check (:173), not a literal — it must stay LAST-ish in the union order because it would swallow any literal if matched first is fine but its openness means literals are what make other types precise. (3) `finish.finishReason` uses `satisfies readonly FinishReason[]` so the wire enum and the model-level FinishReason cannot drift apart (:193-201). (4) Tool chunks carry the full option surface (`providerExecuted`, `providerMetadata`, `toolMetadata`, `dynamic`, `title`, `preliminary`) OPTIONAL and never-gated — same never-gate philosophy as the client state union (pass 8). (5) `custom.kind` enforces the dotted namespace `${string}.${string}` at :140 via transform. Porters who use strict objects break forward-compat silently on the first new field.

**Probe:** `bash -c "grep -n 'rejects chunk types unknown to the client' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/ui-message-chunks.test.ts && grep -n 'value.startsWith' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/ui-message-chunks.ts"` → `:78` and `:173`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "uiMessageChunkSchema DataUIMessageChunk", limit: 3 });
// → ai.packages.ai.src.ui-message-stream.ui-message-chunks.DataUIMessageChunk Type :217-224 (schema itself is module-scope const)
```

## Verdict
Adopt loose-object union validation with field-level forward compatibility and a predicate-typed data-chunk family. Adapt member list to your protocol's feature set. Omit the schema entirely only if your transport never validates at a boundary.
