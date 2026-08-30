<!-- capsule-v2 -->
# acp-stdio-connection-bootstrap — how do you run a JSON-RPC agent bridge over stdio without ever corrupting the protocol stream?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When stdin/stdout ARE the transport, where do diagnostics, lazy imports, and process lifetime go?

## stdout-is-protocol discipline; lazy dual import; per-connection agent factory; park on connection.closed; headless-constrained OAuth
**Path/Symbol:** `apps/cli/src/acp/index.ts` (`runAcpMode` :8-29) + `apps/cli/src/acp/auth.ts` (`performOAuthLogin` :34-70; `authenticateAcpProvider` :96-106).
**Signature:** `runAcpMode(options?: {autoApproveTools?: boolean}): Promise<void>` — resolves only when the connection closes.
**Data Shape:** One `AgentSideConnection` per process; its factory returns a FRESH `AcpAgent(conn)` per client connection. Diagnostics are free-form stderr strings prefixed `[acp]` / `[acp/auth]`.

### Decisive source
```ts
const { AgentSideConnection, ndJsonStream } = await import("@agentclientprotocol/sdk");
const { AcpAgent } = await import("./acpAgent");          // lazy: only when ACP mode runs
writeDiagnostic("[acp] starting ACP mode over stdio…");   // stderr; NEVER "error:"-labeled
const stream = ndJsonStream(
	Writable.toWeb(process.stdout) as WritableStream<Uint8Array>,
	Readable.toWeb(process.stdin) as ReadableStream<Uint8Array>,
);
const connection = new AgentSideConnection((conn) => new AcpAgent(conn, {…}), stream);
await connection.closed;                                   // park the process
```

**Flow:** runAcpMode ⇒ lazy import ACP SDK + AcpAgent ⇒ stderr diagnostic ⇒ wrap stdin/stdout as a Web NDJSON stream ⇒ construct AgentSideConnection with a per-connection factory ⇒ `await connection.closed`. Auth inherits the constraint: stored credentials checked BEFORE any fresh login; OAuth output → stderr diagnostics; browser opened non-blocking (`open(url,{wait:false})`) with a manual-URL fallback diagnostic; an interactive prompt without a defaultValue REJECTS ("OAuth flow requires interactive input which is unavailable in ACP mode").
**Invariant:** Nothing but RPC frames may touch stdout — the startup diagnostic MUST go to stderr and must not be labeled "error:" (test-pinned byte-exact `"[acp] starting ACP mode over stdio…\n"` plus a not-stringContaining("error:") assertion). Heavy dependencies load only in ACP mode. The process lives exactly as long as the connection.
**Probe:** `grep -cF 'await connection.closed;' apps/cli/src/acp/index.ts` → 1; `grep -cF 'await import("./acpAgent")' apps/cli/src/acp/index.ts` → 1. Direct suite `index.test.ts` (1 case, read whole) pins the byte-exact stderr diagnostic and the absence of an "error:" label. `auth.ts` read whole (no dedicated suite — coverage caveat); headless-rejection string pinned by direct read :46-49.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "runAcpMode stdio ndJsonStream AgentSideConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stdout-is-protocol hygiene (stderr-only diagnostics, never error-labeled), lazy bridge imports, one-connection-per-process with a fresh-agent factory, park-on-closed lifetime, and fail-reject headless OAuth prompts. Adapt diagnostic prefixes and the provider vocabulary (closed trio: cline / cline-pass / openai-codex). Omit Cline's credential storage internals. Coverage: sources+test read whole at pin; MCP coverage check not runnable this session — recorded caveat.
