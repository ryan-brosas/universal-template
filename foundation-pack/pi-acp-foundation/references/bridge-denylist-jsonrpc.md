<!-- capsule-v2 -->
# Bridge transport hardening — how do you deny dangerous IDE tools by default and keep MCP client internals from drifting between transports?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How should a bridge that exposes a remote IDE's MCP server filter its tool surface, and how do multiple JSON-RPC transports share one settlement kernel without copy-paste drift?

## Default denylist + shared JSON-RPC settlement + SSE close semantics
**Path/Symbol:** `src/acp/mcp-bridge.ts` (`DEFAULT_IDE_DENYLIST` :135-141, `extraAllowSet`, `isDefaultDenied` :143-152, invalid-stdio degrade :473-481) + `src/acp/mcp-json-rpc.ts` whole file (NEW 45L: `settlePendingJsonRpcResponse`) + `src/acp/mcp-sse.ts` (`#readStream` error-path rewrite :247-276, `streamFailure` capture :250-266) + `src/acp/mcp-stdio.ts` (`requestWithId` REMOVED).
**Signature:** `export function isDefaultDenied(remoteName: string, extra: ReadonlySet<string>): boolean`; `export function settlePendingJsonRpcResponse(message: JsonRpcMessage, pending: Map<string, PendingJsonRpcRequest>): boolean`.
**Data Shape:** deny = prefix rule (`xdebug_*`) ∪ explicit names (`execute_tool`, `xdebug_set_breakpoint`, `xdebug_start_debugger_session`, `xdebug_control_session`), minus env opt-in `PI_ACP_IDE_EXTRA_TOOLS` (comma-separated remote names; NEVER implies AllowAll).

### Decisive source
```ts
// mcp-json-rpc.ts — the ONE settlement point both stdio and SSE now call:
export function settlePendingJsonRpcResponse(message: JsonRpcMessage, pending): boolean {
  if (message.id === undefined || message.id === null) return false   // notification
  const key = String(message.id)
  const entry = pending.get(key)
  if (!entry) return false                                            // unmatched frame
  clearTimeout(entry.timer); pending.delete(key)
  if (message.error) entry.reject(new Error(message.error.message ?? `MCP error ${message.error.code ?? 'unknown'}`))
  else entry.resolve(message.result)
  return true
}
```

**Flow:** every discovered remote tool passes `isDefaultDenied` BEFORE catalog insertion; denials become a diagnostic naming the re-allow env var. An invalid stdio descriptor (args/env not both arrays) no longer throws out of discovery — it marks `#catalogComplete = false` with a phase-tagged diagnostic (`phase=descriptor_validation`) and continues with remaining servers. The duplicate pending-settlement code in sse/stdio collapsed into the shared helper; SSE stream reader restructured so natural stream END and mid-stream ERROR converge on one failure path (`streamFailure ?? SseMcpError('close', …)`), fixing an await-inside-Promise.race operand bug in `close()`. `requestWithId` deleted from StdioMcpClient — dead surface.
**Invariant:** denial happens at catalog-build time so denied tools are never ADVERTISED to the agent (not merely blocked at call time); the denylist is PREFIX-open because the live IDE catalog keeps growing new xdebug_* names; notifications and unknown-id frames are silently ignored by contract (return false).
**Probe:** `npx tsx --test test/unit/default-ide-deny-list.test.ts test/unit/mcp-json-rpc.test.ts test/unit/mcp-sse.test.ts` (prefix/explicit/opt-in matrix; settlement incl. notifications + unknown ids) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "isDefaultDenied settlePendingJsonRpcResponse DEFAULT_IDE_DENYLIST", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt default-deny for execution/debugger/breakpoint tool classes with prefix matching plus explicit reviewed opt-in, phase-tagged degradation instead of throw on bad descriptors, and a single shared JSON-RPC settlement helper across transports. Adapt the denylist names to your IDE's dangerous surface. Omit SSE specifics if your host is stdio-only. Direct tests executed green at the pin.
