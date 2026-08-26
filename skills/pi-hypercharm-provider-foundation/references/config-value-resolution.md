<!-- capsule-v2 -->
# pi config-value resolution semantics — how does `!command` / `$VAR` interpolation work for stored credentials?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you resolve a credential string that may be a literal, an environment reference, or a shell command — exactly the way the pi agent itself does?

## resolveConfigValue + resolveApiKey
**Path/Symbol:** `scripts/update-models.js:49-109` (`resolveConfigValue`), `scripts/update-models.js:116-128` (`resolveApiKey`, `AUTH_JSON_PATH` :40), agent-dir override `scripts/update-models.js:30-38` (`piAgentDir`).
**Signature:** `resolveConfigValue(config: string, env?: object): string | undefined`; `resolveApiKey(): string | undefined`.
**Data Shape:** auth.json credential `{ type: "api_key", key: string }` where `key` is any config value; env fallback `HYPERCHARM_API_KEY`.

### Decisive source
```js
if (config.startsWith('!')) {
    const out = execSync(config.slice(1), { encoding: 'utf8', timeout: 10000,
      stdio: ['ignore', 'pipe', 'ignore'] });
    return out.trim() || undefined;
}
// "$$"/"$!" escape a literal; "${VAR}" braced or $VAR bare (ENV_NAME_RE-validated);
// unset referenced var ⇒ whole value undefined (never partially interpolated)
if (value === undefined) return undefined;
```
Precedence (`resolveApiKey`): stored `hypercharm` credential in `<agentDir>/auth.json` wins → then `process.env.HYPERCHARM_API_KEY` → else undefined and main() exits 1.

**Flow:** read auth.json (missing/unparseable silently falls through) → check `type === "api_key"` → resolve the key STRING through config-value semantics → fall back to env var.
**Invariant:** resolution must MATCH pi's own `resolve-config-value.ts` semantics or the script reads a DIFFERENT key than the runtime uses. Escapes first: `$$` → literal `$`, `$!` → literal `!`. A bare `$` not followed by a valid name stays literal. Unset variable ⇒ ENTIRE value undefined — never empty-string partial output (prevents shipping half a key). Shell commands get a hard 10s timeout and stderr discarded; empty trimmed stdout counts as failure.
**Probe:** no direct test upstream — deterministic probe: the function's doc comment cites its source of truth ("pi's semantics (resolve-config-value.ts in pi-mono)"); porters should diff against that file. Coverage caveat recorded.
**Coverage caveat:** scripts path verified `no_recorded_issue`; behavior untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "resolveConfigValue", limit: 5 });
// → pi-hypercharm-provider.scripts.update-models.resolveConfigValue Function scripts/update-models.js 49-109
```

## Verdict
Adopt the escape rules and all-or-nothing interpolation whenever reimplementing pi-compatible credential strings. Adapt storage location. Omit nothing in the parser — each branch encodes a pi-mono compatibility decision.
