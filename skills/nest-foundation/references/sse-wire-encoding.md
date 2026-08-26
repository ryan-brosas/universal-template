<!-- capsule-v2 -->
# SseStream wire encoding — multiline field serialization, comment-only id suppression, deferred headers

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What exact bytes does an SSE message produce, when are `id:` lines auto-generated vs preserved, and why are headers written on the first transform instead of at pipe time?

## _transform / writeMessage / commitHeaders
**Path/Symbol:** `packages/core/router/sse-stream.ts:_transform` (:140-158), `writeMessage` (:163-177), `commitHeaders` (:111-138), `serializeSseLines` (:6-11).
**Signature:** `_transform(message: MessageEvent, encoding, callback)`; `writeMessage(message, cb: (error) => void)`; objectMode stream.
**Data Shape:** MessageEvent = `{ data?, type?, id?, retry?, comment? }`; output is W3C `text/event-stream` framing.

### Decisive source
```ts
function serializeSseLines(value, prefix) {
  return value.split(/\r\n|\r|\n/).map(line => `${prefix}${line}\n`).join('');
}
// _transform order: event:, id:, retry:, comment (multiline-safe), data, then blank line
data += !isNil(message.comment) ? toCommentString(message.comment) : '';
data += !isNil(message.data) ? toDataString(message.data) : '';
data += '\n';
this.push(data);

public writeMessage(message, cb) {
  if (isNil(message.id) && !isCommentOnly(message)) {
    this.lastEventId!++;                    // auto-id ONLY for data-bearing messages
    message.id = this.lastEventId!.toString();
  }
  if (!this.write(message, 'utf-8')) this.once('drain', cb);
  else process.nextTick(cb);
}
```

**Flow:** every `_transform` first calls `commitHeaders()` → fields serialize in fixed order with CR/LF/CRLF split into repeated prefixed lines (a JSON payload containing newlines still yields legal `data:` lines) → blank line terminates the event → direct `writeMessage` bypasses backpressure via drain/nextTick callback.
**Invariant:** Comment-ONLY messages (`comment` set, data/type/retry undefined — `isCommentOnly`) never consume an auto id; explicit `id: 0` is preserved because only `isNil` gates. Headers stay unwritten through `pipe()` and are deferred until the FIRST message (or macrotask commit from the controller) so an early error can still change status codes. Socket tuning (`setKeepAlive/setNoDelay/setTimeout(0)`) happens in the constructor from the request.
**Probe:** `packages/core/test/router/sse-stream.spec.ts` ("writes multiple multiline messages", "only skips generated ids for comment-only messages", "preserves explicit id of 0 in writeMessage", "does not write headers eagerly in pipe()").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "SseStream commitHeaders writeMessage", limit: 5 });
```

## Verdict
Adopt the field-order + newline-splitting + comment-only-id-suppression rules as a unit — they define wire compatibility; adapt transport plumbing; omit retry/comment support only if clients can't handle them. Porting wrong: naive `${data}\n` breaks multiline payloads, and generating ids for comments corrupts client LastEventId reconnection.
