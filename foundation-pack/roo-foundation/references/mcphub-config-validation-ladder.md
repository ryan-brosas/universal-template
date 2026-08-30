<!-- capsule-v2 -->
# McpHub config validation ladder — how do you validate a mixed stdio/SSE/streamable-http server config so bad shapes fail LOUDLY before a transport is ever built?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does the hub validate server configs so that stdio fields never mix with url fields, type is inferred or demanded correctly, and every failure surfaces a human-readable message naming the server?

## Pre-schema triage + discriminated-union Zod schema
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`validateServerConfig`, :215–273; error-message consts :76–86; `createServerTypeSchema`/`ServerConfigSchema`/`McpSettingsSchema` :89–148).
**Signature:** `private validateServerConfig(config: any, serverName?: string): z.infer<typeof ServerConfigSchema>`.
**Data Shape:** input raw per-server object from mcp.json; output = one of three fully-discriminated branches, each extending `BaseConfigSchema` (`disabled?`, `timeout: 1..3600 default 60`, `alwaysAllow: string[] default []`, `watchPaths?`, `disabledTools: string[] default []`) plus branch fields: stdio `{command: min(1), args?, cwd: default workspaceFolder??process.cwd(), env?}`, sse `{url: z.string().url(), headers?}`, streamable-http `{url, headers?}`. Cross-branch exclusion enforced with `z.undefined().optional()` sentinels (`url`/`headers` forbidden in stdio; `command`/`args`/`env` forbidden in url branches). Each branch `.transform`s `type` to its literal and `.refine`s it.

### Decisive source
```ts
// :217-233 — pre-schema triage BEFORE zod ever runs
const hasStdioFields = config.command !== undefined
const hasUrlFields = config.url !== undefined // Covers sse and streamable-http
if (hasStdioFields && hasUrlFields) {
    throw new Error(mixedFieldsErrorMessage)          // "Cannot mix 'stdio' and ('sse' or ...)"
}
if (!config.type && hasStdioFields) { config.type = "stdio" }   // type INFERRED for stdio
if (hasUrlFields && !config.type) {
    throw new Error("Configuration with 'url' must explicitly specify 'type' as 'sse' or 'streamable-http'.")
}
```
```ts
// :99 — cross-field exclusion inside the stdio branch
url: z.undefined().optional(),
headers: z.undefined().optional(),
```
```ts
// :260-269 — ZodError → single joined message, optionally server-scoped
if (validationError instanceof z.ZodError) {
    const errorMessages = validationError.errors.map((err) => `${err.path.join(".")}: ${err.message}`).join("; ")
    throw new Error(serverName ? `Invalid configuration for server "${serverName}": ${errorMessages}` : ...)
}
```

**Flow:** triage throws (`mixed` → infer stdio type → url-without-type throw → unknown-type throw :236–238 → declared-vs-fields mismatch throws :241–249 → neither command nor url throw :252) then `ServerConfigSchema.parse`; on `ZodError` rethrow as one `path: message; …` string.
**Invariant:** a config that survives this function is fully typed and single-transport; `type` for url-based servers must be user-supplied (never guessed), while stdio's is inferred — the asymmetry is deliberate. Note the schema-level `timeout` DEFAULT (60) exists but the call path re-reads timeouts defensively at callTool time (:1748–1753) because stored configs are JSON strings parsed lazily — do not assume parse-time defaults reach runtime reads.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"timeout configuration"` → it `"should validate timeout values"` (:1468–1487) pins `timeout: 0 / -1 / 3601` all THROW while `timeout: 60` parses.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "validateServerConfig ServerConfigSchema mixed fields", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.validateServerValid Method src/services/mcp/McpHub.ts 215-273 (total: 7)
```

## Verdict
Adopt the pre-schema triage order and the discriminated-union-with-forbidden-fields shape — porting straight to a single flat schema loses both the loud mixed-fields error and the stdio/url type asymmetry. Adapt the exact English error strings and i18n keys. Omit nothing here; this function is the gate every other seam trusts.
