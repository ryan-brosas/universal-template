<!-- capsule-v2 -->
# JSON import streaming — how do you parse arbitrarily large JSON files as row streams, arrays or not?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the JSON handler turn a Readable into per-row yields while surviving malformed input and non-array roots?

## Peek/unshift + bracket-wrap + error-forwarded pipeline
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/handlers/json-import.handler.ts` — `buildJsonArrayStream` error-forwarding (:21-38), `flattenObject` depth cap (:19, :44-66), `peekJsonType` unshift probe (:72-130), `wrapAsArray` empty-source flush (:136-160), preview premature-close tolerance (:183-205), streamRows NO-tolerance comment (:270-272), path-based column resolution (:256-261, :295-307).
**Signature:** `peekJsonType(readStream) → {isArray, stream}`; `wrapAsArray(stream)` prepends `[` on first chunk and appends `]` in flush; consumed via `for await (const {value} of parser().pipe(streamArray()) pipeline)`.
**Data Shape:** nested keys flatten to `a_b` joined paths (depth ≤ 3, deeper objects JSON-stringified); column `meta.path = ['a','b']` records the origin path for re-resolution at stream time.

### Decisive source
```ts
// `.pipe()` does NOT forward 'error' events downstream, so a parser error
// … becomes an uncaughtException that crashes the process.
function buildJsonArrayStream(jsonStream: Readable): Transform {
  const parserStream = parser(); const arrayStream = streamArray();
  const forwardError = (err: Error) => arrayStream.destroy(err);
  jsonStream.on('error', forwardError);
  parserStream.on('error', forwardError);
  jsonStream.pipe(parserStream).pipe(arrayStream);
  return arrayStream as Transform;
}
// peek: read first chunk, find first non-whitespace byte…
isArray = byte === 0x5b; // '['
readStream.unshift(chunk);            // push the chunk back so the stream is unconsumed
```

**Flow:** preview and streamRows BOTH start by peeking the first non-whitespace byte (skipping space/tab/CR/LF/BOM) and unshifting it back → single-object payloads get wrapped as a synthetic `[ … ]` array (flush emits `[]` for empty sources) → the piped parser/array stream is consumed with `for await`, flattening rows and resolving each column through its recorded path → preview tolerates `ERR_STREAM_PREMATURE_CLOSE` only if some rows were already sampled; streamRows deliberately does NOT — mid-stream aborts must surface so partial-success stats are honest.
**Invariant:** the error-forwarding shim is MANDATORY — plain `.pipe()` drops upstream 'error' events, and an unlistened parser error becomes an uncaughtException that kills the whole process. The preview-vs-import asymmetry (tolerate truncation when sampling vs never tolerate during real import) is intentional, not sloppy. Empty input must still yield valid empty output (`wrapAsArray.flush` emits the `[`).
**Probe:** no unit test upstream. Source-grounded probe: crash-race comment :22-28; BOM byte `0xef` in skip list :100; paired comments :195-198 vs :270-272 state the tolerance split verbatim.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JsonImportHandler peekJsonType wrapAsArray buildJsonArrayStream ERR_STREAM_PREMATURE_CLOSE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt peek-unshift + wrap + explicit error forwarding for any stream-JSON ingestion; adapt flatten depth to your column limits; omit path-columns if your imports are flat.
