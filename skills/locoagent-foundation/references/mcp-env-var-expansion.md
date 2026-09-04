<!-- capsule-v2 -->
# Env-var expansion in configs — how do ${VAR} and ${VAR:-default} expand in MCP server definitions without silently dropping unset variables?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the expansion syntax, default-value rule, and missing-variable reporting contract?

## Regex replace with missing-collection and literal passthrough
**Path/Symbol:** `src/services/mcp/envExpansion.ts` (whole :1-38): `expandEnvVarsInString`; consumer `expandEnvVars` walks command/args/env/url/headers per config type (config.ts :556-616) and reports via validation errors with remediation suggestion (:1330-1348).
**Signature:** `expandEnvVarsInString(value: string): {expanded: string, missingVars: string[]}`.
**Data Shape:** `\$\{([^}]+)\}` capture; split on `':-'` limit 2 (defaults may themselves contain `:-`); missing vars leave the ORIGINAL `${VAR}` text in place AND get reported.

### Decisive source
```ts
const expanded = value.replace(/\$\{([^}]+)\}/g, (match, varContent) => {
  // Split on :- to support default values (limit to 2 parts to preserve :- in defaults)
  const [varName, defaultValue] = varContent.split(':-', 2)
  const envValue = process.env[varName]
  if (envValue !== undefined) return envValue
  if (defaultValue !== undefined) return defaultValue
  // Track missing variable for error reporting
  missingVars.push(varName)
  // Return original if not found (allows debugging but will be reported as error)
  return match
})
```

**Flow:** config parse (expandVars=true) → every string field expanded per type (stdio: command/args/env; remote: url/headers; sdk/claudeai-proxy/ide types untouched) → deduped missingVars become warning-severity validation errors naming each var and suggesting `Set the following environment variables: ...` — the server entry still loads so /mcp can show it.
**Invariant:** Never drop or empty-expand an unset variable — leaving `${VAR}` visible makes the misconfiguration debuggable in logs/UI while the structured error list carries the machine-readable report.
**Probe:** `grep -n "split(':-', 2)" src/services/mcp/envExpansion.ts` (`18:`) and `grep -n 'return match' src/services/mcp/envExpansion.ts` (`31:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "expandEnvVarsInString", limit: 5 });
```

## Verdict
Adopt the function verbatim (38 lines). Adapt field-walking to your config schema. Keep warn-not-drop semantics.
