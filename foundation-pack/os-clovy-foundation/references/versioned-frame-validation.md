<!-- capsule-v2 -->
# Versioned frame validation — what must every inbound line prove before dispatch?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter wiring a stdio JSON-RPC peer must decide which fields are mandatory on every frame and how a bad frame fails.

## Frame parse ladder
**Path/Symbol:** `agent-runtime/src/protocol.ts:parseFrame` (:83-121); helpers `requireString` (:139-143), `isRecord` (:145-147), `ProtocolError` (:71-81).
**Signature:** `function parseFrame(line: string): RpcFrame` (throws `ProtocolError`).
**Data Shape:** `FrameBase = { jsonrpc:"2.0", protocolVersion:1, sessionId:string, runId:string, sequence:number }`; frame is one of `RpcRequest{id,method,params}` / `RpcResponse{id,result|error}` / `RuntimeEvent{eventId,method,params}`. Empty lines never reach the parser (`NdjsonRpcPeer.listen` skips them).

### Decisive source
```ts
if (!isRecord(value) || value.jsonrpc !== "2.0") {
  throw new ProtocolError(-32600, "Invalid JSON-RPC frame");
}
if (value.protocolVersion !== PROTOCOL_VERSION) {
  throw new ProtocolError(-32001,
    `Unsupported protocol version: ${String(value.protocolVersion)}`);
}
requireString(value, "sessionId");
requireString(value, "runId");
if (!Number.isSafeInteger(value.sequence) || Number(value.sequence) < 0) {
  throw new ProtocolError(-32600, "Frame sequence must be a non-negative integer");
}
if ("method" in value) { /* request or event: params must be an object */ }
else { requireString(value, "id"); /* response must contain result or error */ }
```

**Flow:** JSON.parse failure → `-32700 Invalid JSON` → record check + jsonrpc check → `-32600` → protocolVersion mismatch → `-32001` (before any dispatch) → per-key non-empty-string checks → sequence check → method-branch discriminates request/event by `eventId`, else response needs `result` XOR `error`.
**Invariant:** An unsupported version is rejected before semantic dispatch; every frame — including events and responses — carries session/run/sequence identity; sequences are per-`sessionId\0runId` counters allocated by the writer (`NdjsonRpcPeer.nextSequence` :174-179).
**Probe:** `agent-runtime/test/protocol.test.ts` — "rejects unknown protocol versions before dispatch" (asserts code -32001), "rejects malformed JSON and invalid sequences" (asserts -32700 message and `/non-negative integer/`). Executed live at pin: 17/17 across the four dependency-free suites.

## Get live surrounding code
**Retrieve:** executed at pin (top hit = target):
```
search_graph({ project:"os-clovy", query:"protocol version frame validation sequence", file_pattern:"agent-runtime/*" })
→ os-clovy.agent-runtime.src.protocol.parseFrame Function agent-runtime/src/protocol.ts 83-121  (rank 1)
   os-clovy.agent-runtime.src.protocol.encodeFrame ... 123-125
```

## Verdict
Adopt the validation ladder, the typed error codes, and identity-on-every-frame (it makes host-side run routing stateless). Adapt the version constant and method tables (`HOST_REQUEST_METHODS`, `RUNTIME_*`) to your vocabulary. Omit nothing structural; but note the discriminator asymmetry — `isRequest` = has `method` and no `eventId`, so a method string without `eventId` can never be an event.
