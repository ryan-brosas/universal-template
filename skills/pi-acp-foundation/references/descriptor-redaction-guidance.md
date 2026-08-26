<!-- capsule-v2 -->
# Bridge descriptor redaction + guidance rendering — what may a debug log or a system prompt say about the host's MCP servers?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you log session MCP descriptors without leaking credentials, and how is IDE-mode guidance composed into (never over) an existing system prompt?

## sanitizeBridgeDescriptors + before_agent_start composition
**Path/Symbol:** `src/acp/agent.ts` (`sanitizeBridgeDescriptors` :1949-1984, `logBridgeDescriptors` caller :1976-1986) + `src/pi-extension/acp-mcp-bridge.ts` (`before_agent_start` registration :486, `renderIdeCodingGuidance` :1480-1548).
**Signature:** `export function sanitizeBridgeDescriptors(mcpServers: NewSessionRequest['mcpServers']): unknown`; hook returns `{ systemPrompt: `${event.systemPrompt}\n\n${text}` } | undefined`.
**Data Shape:** sanitized server record = `{ name, type, command: basename-only when string, args: '[N arg(s), redacted]', env: [{name, value}] }` where value passes ONLY for `IJ_MCP_SERVER_PORT` / `IJ_MCP_SESSION_ID` (local-only keys); every other non-empty value becomes `[redacted <len> chars]`; non-array env → `'[redacted non-array env]'`.

### Decisive source
```ts
value:
  item.name === 'IJ_MCP_SERVER_PORT' || item.name === 'IJ_MCP_SESSION_ID'
    ? item.value
    : item.value ? `[redacted ${String(item.value).length} chars]` : undefined,
```

**Flow:** `PI_ACP_DEBUG_BRIDGE=1` logs the SANITIZED structure only (redaction extracted from inline logging so tests can pin it — `bridge-descriptor-redaction.test.ts`). Guidance: on every agent start under ide-mode, the extension appends state-aware instructions — active mode names each registered capability tool explicitly ("apply patches with ide_idea_apply_patch"), declares native tools unavailable and bash limited to git/tests/builds; awaiting_catalog differs by mode (required: "Native file tools stay disabled" vs prefer: "remain available temporarily"); native_fallback tells the model not to call stale IDE tool names. Diagnostics accumulated from policy transitions are appended after the guidance text, joined with newlines; empty guidance + empty diagnostics ⇒ return undefined (prompt untouched).
**Invariant:** logging never throws into the session (try/catch around stderr write) and never emits raw env values; guidance APPENDS to the host system prompt rather than replacing it; state transitions are always reflected in the next turn's prompt because the hook re-renders from current state.
**Probe:** `npx tsx --test test/unit/bridge-descriptor-redaction.test.ts` (leak matrix incl. unknown-key redaction lengths) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "sanitizeBridgeDescriptors renderIdeCodingGuidance before_agent_start", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist-only env passthrough in debug logs and append-only, state-aware guidance composition with diagnostic trailing. Adapt the local-only key list to your host's non-secret descriptor fields. Omit IDE-specific guidance wording. Direct test executed green at pin.
