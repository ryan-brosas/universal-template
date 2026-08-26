<!-- capsule-v2 -->
# injectVariables `${env:VAR}` templating — how do you expand VSCode-style variables inside an MCP server config without mutating the original or crashing on missing vars?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How are `${env:NAME}` and `${workspaceFolder}` references resolved in server configs before transport construction?

## Stringify → regex-replace → re-parse; missing nested vars keep the literal + warn
**Path/Symbol:** `src/utils/config.ts` (`injectVariables` :35–66; convenience `injectEnv` :20–22). Consumed at `McpHub.ts` :700–704 with `{ env: process.env, workspaceFolder: <first folder fsPath ?? ""> }`.
**Signature:** `async function injectVariables<C extends InjectableConfigType>(config: C, variables: Record<string, undefined | null | string | Record<string, undefined | null | string>>, propNotFoundValue?: any)`.
**Data Shape:** two variable kinds: plain string values replace `${key}` globally (paths normalized via `.toPosix()`); RECORD values drive the nested pattern `${key:NAME}` where NAME is `\w+`. `null`/`undefined` variable entries are skipped entirely.

### Decisive source
```ts
// :48 — plain replacement, path-normalized
configString = configString.replace(new RegExp(`\\$\\{${key}\\}`, "g"), value.toPosix())
```
```ts
// :51-61 — nested ${env:NAME} with not-found policy
configString = configString.replace(new RegExp(`\\$\\{${key}:([\\w]+)\\}`, "g"), (match, name) => {
    const nestedValue = value[name]
    if (nestedValue == null) {
        console.warn(`[injectVariables] variable "${name}" referenced but not found in "${key}"`)
        return propNotFoundValue ?? match          // keeps the LITERAL when no default supplied
    }
    return typeof nestedValue === "string" ? nestedValue.toPosix() : nestedValue
})
```

**Flow:** objects are JSON.stringify'd once → every variable kind does global regex replacement over the string → JSON.parse back (so the original object is never mutated and non-string JSON types survive). McpHub passes process.env as a NESTED record, hence configs write `${env:API_KEY}`, plus `${workspaceFolder}` as a plain string var.
**Invariant:** missing env vars must NOT throw or empty the field by default — the match is preserved literally and a warning logged, so a config referencing a not-yet-set secret still round-trips visibly; replacement happens on the stringified form, which means injected values containing JSON-special characters are inserted RAW (a value with a quote can corrupt the JSON — known sharp edge to respect when porting).
**Probe:** direct spec: `src/utils/__tests__/config.spec.ts` (pins `${env:X}` expansion, missing-var literal retention, object immutability); hub-side integration via Windows-wrapping suite asserting `env: expect.objectContaining({ FNM_DIR: ... })` (:2320–2330).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "injectVariables env workspaceFolder", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → Function src/utils/config.ts injectVariables 35-66 (total: 50)
```

## Verdict
Adopt stringify-replace-parse with warn-and-keep-literal semantics. Adapt the pattern syntax if your host uses different delimiters. Omit nothing.
