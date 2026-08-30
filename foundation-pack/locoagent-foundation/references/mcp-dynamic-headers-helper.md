<!-- capsule-v2 -->
# Dynamic headers helper — how do I inject fresh auth headers at connect time from an untrusted config without executing it before trust is established?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What are the trust-gate, timeout, env-contract, and fail-open rules for a headersHelper command?

## Trust-gated exec → 10s timeout → strict JSON-string validation → null not throw
**Path/Symbol:** `src/services/mcp/headersHelper.ts`: trust check (:40-57), exec (:59-76), validation (:77-98), combiner `getMcpServerHeaders` (:125-138).
**Signature:** `getMcpHeadersFromHelper(serverName, config): Promise<Record<string,string> | null>`; exec via `execFileNoThrowWithCwd(config.headersHelper, [], {shell:true, timeout:10000, env:{...process.env, CLAUDE_CODE_MCP_SERVER_NAME, CLAUDE_CODE_MCP_SERVER_URL}})`.
**Data Shape:** helper prints a JSON object of string→string on stdout; non-zero exit or empty stdout = error.

### Decisive source
```ts
// Security check for project/local settings
// Skip trust check in non-interactive mode (e.g., CI/CD, automation)
if ('scope' in config &&
    isMcpServerFromProjectOrLocalSettings(config as ScopedMcpServerConfig) &&
    !getIsNonInteractiveSession()) {
  const hasTrust = checkHasTrustDialogAccepted()
  if (!hasTrust) {
    // logAntError('MCP headersHelper invoked before trust check', ...) + telemetry
    return null                       // refuse execution, don't crash connect
  }
}
...
// Pass server context so one helper script can serve multiple MCP servers
// (git credential-helper style). See deshaw/anthropic-issues#28.
env: { ...process.env,
       CLAUDE_CODE_MCP_SERVER_NAME: serverName,
       CLAUDE_CODE_MCP_SERVER_URL: config.url },
// every value validated typeof 'string' else throw → caught → return null:
// "Return null instead of throwing to avoid blocking the connection"
// getMcpServerHeaders: dynamic overrides static — {...staticHeaders, ...dynamicHeaders}
```

**Flow:** transport construction calls getMcpServerHeaders → static config.headers + helper-derived dynamic headers merged with DYNAMIC WINNING (rotated tokens beat stale config) → combined map feeds SSE requestInit / ws headers / http requestInit.
**Invariant:** A repo-provided (.mcp.json scope=project/local) command must never run before workspace trust (and never blocks CI); helper failure degrades to static headers only — connection proceeds.
**Probe:** `grep -n 'CLAUDE_CODE_MCP_SERVER_NAME: serverName,' src/services/mcp/headersHelper.ts` (`68:`) and `grep -n 'timeout: 10000,' src/services/mcp/headersHelper.ts` (`63:`) and `grep -n 'checkHasTrustDialogAccepted()' src/services/mcp/headersHelper.ts | head -1` (`48:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getMcpServerHeaders", limit: 5 });
```

## Verdict
Adopt trust-before-exec, context-env contract, strict shape validation, fail-open-to-static merge order. Adapt env var names.
