<!-- capsule-v2 -->
# In-process and control-channel transports — how do MCP servers run without spawning a process?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What do the linked in-process transport pair and the SDK control-message bridge look like, and what are their failure semantics?

## queueMicrotask delivery + paired close + sendMcpMessage callback bridge
**Path/Symbol:** `src/services/mcp/InProcessTransport.ts` (whole file :1-63): `InProcessTransport` private `peer`/`closed`, `_setPeer`, `createLinkedTransportPair(): [Transport, Transport]`; `src/services/mcp/SdkControlTransport.ts`: `SdkControlClientTransport` (:60-95), `SdkControlServerTransport` (:109-136), architecture header (:1-37).
**Signature:** pair: `send()` → `queueMicrotask(() => this.peer?.onmessage?.(message))`; close marks BOTH sides closed and fires both oncloses; client bridge constructor `(serverName: string, sendMcpMessage: SendMcpMessageCallback)`.
**Data Shape:** Both implement the MCP SDK `Transport` surface (`start/send/close` + `onclose/onerror/onmessage`); closed transports throw on send.

### Decisive source
```ts
async send(message: JSONRPCMessage): Promise<void> {
  if (this.closed) throw new Error('Transport is closed')
  // Deliver to the other side asynchronously to avoid stack depth issues
  // with synchronous request/response cycles
  queueMicrotask(() => { this.peer?.onmessage?.(message) })
}
async close(): Promise<void> {
  if (this.closed) return
  this.closed = true
  this.onclose?.()
  // Close the peer if it hasn't already closed
  if (this.peer && !this.peer.closed) {
    this.peer.closed = true
    this.peer.onclose?.()
  }
}
// CLI-side SDK bridge: send() awaits sendMcpMessage(serverName, message) — a full
// request/response round trip through stdout/stdin control messages — then feeds
// the response to onmessage. Message IDs are preserved end-to-end for correlation;
// multiple SDK MCP servers multiplex via server_name on the wrapper.
```

**Flow:** connectToServer uses `createLinkedTransportPair()` for Chrome/ComputerUse servers to avoid spawning ~325MB subprocesses (:905-943 of client.ts) — server.connect(serverTransport), Client connects with clientTransport. setupSdkMcpClients builds one SdkControlClientTransport per dynamic SDK server over the shared `sendMcpMessage` callback (:3262-3348 of client.ts).
**Invariant:** In-process delivery MUST be async (queueMicrotask) or nested request/response cycles blow the stack; closing one side must close the peer exactly once; the control-bridge keeps protocol message IDs intact across the process boundary.
**Probe:** `grep -n 'queueMicrotask(() =>' src/services/mcp/InProcessTransport.ts` (`32:`) and `grep -n 'this.peer.closed = true' src/services/mcp/InProcessTransport.ts` (`45:`) and `grep -n 'sendMcpMessage(this.serverName, message)' src/services/mcp/SdkControlTransport.ts` (`80:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createLinkedTransportPair", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SdkControlClientTransport", limit: 5 });
```

## Verdict
Adopt both transport shapes wholesale (~200 lines total). Adapt the control-message envelope to your IPC. Omit nothing — these are complete, portable implementations.
