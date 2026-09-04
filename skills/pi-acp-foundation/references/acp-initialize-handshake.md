<!-- capsule-v2 -->
# ACP initialize/authenticate handshake — what must an adapter declare before any session exists?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an ACP agent answer `initialize` (protocol version, capabilities, auth methods) so heterogeneous clients (Zed, JetBrains) can connect without version negotiation failing?

## Handshake declaration
**Path/Symbol:** `src/acp/agent.ts:PiAcpAgent.initialize` (:343-390), `PiAcpAgent.authenticate` (:565-569); `src/acp/auth.ts:getAuthMethods`.
**Signature:** `initialize(params: InitializeRequest): Promise<InitializeResponse>`; `authenticate(_params): Promise<void>`.
**Data Shape:** Response = `{ protocolVersion, agentInfo{name,title,version,_meta}, authMethods[], agentCapabilities{loadSession,providers,mcpCapabilities,promptCapabilities,sessionCapabilities} }`. `_meta.piAcp.build` carries tsup-injected build provenance.

### Decisive source
```ts
// We currently only support ACP protocol version 1.
const supportedVersion = 1
const requested = params.protocolVersion

return {
  protocolVersion: requested === supportedVersion ? requested : supportedVersion,
  ...
  // Zed currently uses ClientCapabilities._meta["terminal-auth"] to decide whether to show
  // the "Authenticate" banner/button. If not supported, we still return the method for the registry.
  authMethods: getAuthMethods({
    supportsTerminalAuthMeta: (params as any)?.clientCapabilities?._meta?.['terminal-auth'] === true
  }),
  agentCapabilities: {
    loadSession: true,
    providers: {},
    mcpCapabilities: { http: false, sse: false, acp: true },
    promptCapabilities: {
      image: true,
      audio: false,
      embeddedContext: process.env.PI_ACP_ENABLE_EMBEDDED_CONTEXT === 'true'
    },
    sessionCapabilities: {
      // **UNSTABLE** ACP capability used by Zed's codex-acp adapter.
      list: {}, delete: {}, fork: {}, resume: {}, close: {}
    }
  }
}
```
```ts
async authenticate(_params: AuthenticateRequest) {
  // Terminal Auth is handled out-of-band by re-launching the binary with `--terminal-login`.
  // If the client calls `authenticate` anyway, we can no-op successfully.
  return
}
```

**Flow:** Client sends `initialize` → adapter echoes the requested version only when it equals the single supported version, otherwise replies with its own (never rejects) → declares capability surface incl. unstable session lifecycle and ACP-only MCP transport (`acp:true`, http/sse false because bridging happens adapter-side) → auth methods carry a Zed-specific `_meta['terminal-auth']` block (`{command, args:['--terminal-login'], label}`) gated on a client-capability probe. A later `authenticate` call is a deliberate success no-op because real terminal login is an out-of-band re-launch.
**Invariant:** Version mismatch degrades to "reply with supported version", never an error; auth methods are ALWAYS returned (registry completeness), only the Zed banner `_meta` is conditional; capability flags must match actual implemented methods or clients will call missing RPCs.
**Probe:** `test/unit/auth-methods-terminal-auth-meta.test.ts` ("getAuthMethods: includes Zed terminal-auth metadata when enabled" pins `_meta['terminal-auth'].args == ['--terminal-login']`; disabled variant pins its absence) + `test/unit/pi-enable-embed-context-flag.test.ts` (embeddedContext env gate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "initialize agentCapabilities authMethods protocolVersion agentInfo", limit: 10 });
// -> pi-acp.src.acp.agent.PiAcpAgent.initialize src/acp/agent.ts 343-390
```

## Verdict
Adopt the echo-or-degrade protocol-version rule, always-populated authMethods with conditional client-probe `_meta`, and capability flags that exactly mirror implemented methods. Adapt the build-provenance `_meta` payload and env-gated prompt capabilities to your host. Omit the terminal-auth re-launch contract unless your host also authenticates by re-executing the binary. Coverage: both cited paths `no_recorded_issue` at gen-matched full index.
