<!-- capsule-v2 -->
# Native-messaging bridge host — how does a stdio process relay between the Chrome extension's framing and N local MCP clients over one Unix socket?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the message topology, framing, and lifecycle of a Chrome native messaging host that fans tool traffic out to per-PID MCP clients?

## chrome-native-host-relay
**Path/Symbol:** `src/utils/claudeInChrome/chromeNativeHost.ts` (`runChromeNativeHost` :59-82, `ChromeNativeHost` :103-434, `ChromeMessageReader` :440-527, `MAX_MESSAGE_SIZE` :27).
**Signature:** `sendChromeMessage(message: string): void` (4-byte LE length prefix + UTF-8 JSON on **stdout**, Chrome's native-messaging protocol); inbound from Chrome read via async `ChromeMessageReader.read(): Promise<string | null>`; MCP-client side = `net.Server` on a per-PID Unix socket with its own identical 4-byte-LE framing.
**Data Shape:** Chrome→host messages are `{type:'ping'|'get_status'|'tool_response'|'notification'|...}` passthrough-validated by zod (`type: z.string()` only); host→MCP requests wrap `{type:'tool_request', method, params}`; MCP responses broadcast verbatim minus their `type` field. `mcpClients: Map<id,{socket,buffer}>`.

### Decisive source
```ts
// eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
while (true) {
  const message = await messageReader.read()
  if (message === null) {
    // stdin closed, Chrome disconnected
    break
  }
  await host.handleMessage(message)
}
await host.stop()
```
plus the reader's Bun constraint:
```ts
// Chrome message reader using async stdin. Synchronous reads can crash Bun, so we use
// async reads with a buffer.
```

**Flow:** Chrome spawns the host as a subprocess speaking framed JSON on stdio → host listens on `<socketDir>/<pid>.sock` → each CLI session connects as an MCP client and gets a buffered socket with frame-splitting (`length===0 || length > MAX_MESSAGE_SIZE(1MB)` ⇒ destroy socket) → `tool_request`s forward to Chrome; `tool_response`/`notification`s strip `type` and BROADCAST to every connected client (no routing by id — clients must correlate); connection/close of any client emits `mcp_connected`/`mcp_disconnected` to the extension.
**Invariant:** stdin EOF is THE shutdown signal (null from `read()` breaks the loop and tears down server + sockets); sync stdin reads crash Bun so reads must stay event-driven; oversized or zero-length frames kill the client socket rather than being skipped — there is no resync in a length-prefixed stream. The pending-resolve race is handled by re-running `tryProcessMessage()` immediately after registering the resolver (:520-525).
**Probe:** no upstream test. Deterministic pins: `grep -n "writeUInt32LE" src/utils/claudeInChrome/chromeNativeHost.ts` → :53/:303/:326/:379 (all four frame sites share MAX_MESSAGE_SIZE=1MB :27); `grep -n "Synchronous reads can crash Bun" src/utils/claudeInChrome/chromeNativeHost.ts` → :437.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runChromeNativeHost sendChromeMessage", limit: 10 });
```

## Verdict
Adopt the dual-framing topology (native-messaging stdout ⇄ per-PID socket) and EOF-driven lifecycle. Adapt the message-type vocabulary to your extension contract. Omit the ant-only debug log file. Coverage caveat: no unit tests upstream.
