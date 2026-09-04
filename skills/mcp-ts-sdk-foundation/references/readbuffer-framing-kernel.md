<!-- capsule-v2 -->
# Newline framing kernel — how does one 62-line buffer class serve both stdio peers while tolerating debug noise but never masking schema violations?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What are ReadBuffer's framing, tolerance, and overflow contracts, and where exactly does "skip a bad line" stop being safe?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/stdio.ts`: `STDIO_DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024` (:4), class `ReadBuffer` (:9-54, `append` :17-24, `readMessage` :26-49), `deserializeMessage` (:56-58), `serializeMessage` (:60-62); instantiators (graph): server `stdio.ts`, client `stdio.ts`; direct test `packages/core-internal/test/shared/stdio.test.ts`.
**Signature:** `append(chunk: Buffer): void` · `readMessage(): JSONRPCMessage | null` · `serializeMessage(message: JSONRPCMessage): string`
**Data Shape:** newline-delimited UTF-8 JSON-RPC frames; internal `Buffer` remainder.

### Decisive source
```ts
// :18-22 — overflow checked BEFORE concat; clear-then-throw (a runaway stream cannot pin memory)
const newSize = (this._buffer?.length ?? 0) + chunk.length;
if (newSize > this._maxBufferSize) { this.clear(); throw new Error(`ReadBuffer exceeded maximum size of ${this._maxBufferSize} bytes`); }
// :33-45 — frame extraction + the tolerance asymmetry
const line = this._buffer.toString('utf8', 0, index).replace(/\r$/, '');
this._buffer = this._buffer.subarray(index + 1);
try { return deserializeMessage(line); }            // JSONRPCMessageSchema.parse(JSON.parse(line))
catch (error) {
    if (error instanceof SyntaxError) { continue; } // non-JSON line: SKIP (tsx/nodemon stdout noise)
    throw error;                                    // valid JSON failing SCHEMA still throws → onerror
}
```

**Flow:** transport data handler appends chunks and loops `readMessage()` until null;
`serializeMessage` is the exact inverse (`JSON.stringify(message) + '\n'`). No newline ⇒ null
(incomplete JSON stays buffered until completed). Empty lines and JSON-looking-but-unparseable
lines are skipped; a parseable object that fails `JSONRPCMessageSchema` propagates.

**Invariant:** the kernel survives arbitrary interleaved junk EXCEPT volume — overflow drops the
whole buffer before throwing so the next append starts clean (exactly-at-limit is legal).
One trailing `\r` is stripped (CRLF interop), interior `\r` untouched. The SyntaxError-vs-schema
asymmetry is deliberate: hot-reload tool chatter must not kill the pipe, but a malformed-but-valid-
JSON protocol message must surface via onerror rather than vanish. Shared by BOTH sides — porting
one side without the other breaks the framing contract.

**Probe:** `packages/core-internal/test/shared/stdio.test.ts` :37-115 (filter matrix: empty lines,
debug lines, interleaved multi-message, incomplete-until-newline :76-83, unbalanced braces,
valid-JSON-schema-failure THROWS :109-114) and :117-158 (default/custom max throw,
clear-before-throw recovery :135-144, exactly-at-limit allowed :146-150).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "typescript-sdk", function_name: "typescript-sdk.packages.core-internal.src.shared.stdio.ReadBuffer.readMessage", direction: "both" });
```

## Verdict
Adopt verbatim for any newline-framed peer channel; adapt `maxBufferSize` to your threat model
(10 MiB default); omit the SyntaxError skip only for channels that cannot receive foreign output.
Companions: stdio-stream-discipline.md (server-side read-loop wiring: parse failures survive,
overflow/EPIPE close), stdio-spawn-disposal-ladders.md (client-side processReadBuffer wiring).
