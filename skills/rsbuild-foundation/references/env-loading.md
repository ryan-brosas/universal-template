<!-- capsule-v2 -->
# Env loading — how are .env files parsed, expanded, prefixed into define vars, and cleaned up?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the file precedence, why NODE_ENV is special-cased twice, and why an empty prefix must throw instead of matching everything.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/loadEnv.ts:DOTENV_LINE` (8–9), `parse` (20–56), `validatePrefixes` (58–80), `loadEnv` (146–222).
**Signature:** `loadEnv({cwd?, mode?, prefixes? = ['PUBLIC_'], processEnv? = process.env}): LoadEnvResult`.
**Data Shape:** result `{parsed: Record<string,string>, filePaths: string[], rawPublicVars, publicVars: {'process.env.KEY' | 'import.meta.env.KEY': JSON.stringify(val)}, cleanup(): void}`.

### Decisive source
```ts
// precedence order — later files override earlier keys via Object.assign accumulation
const filenames = ['.env', '.env.local', `.env.${mode}`, `.env.${mode}.local`];
const filePaths = filenames.map(f => join(cwd, f)).filter(isFileSync);
for (const envPath of filePaths) Object.assign(parsed, parse(fs.readFileSync(envPath)));

// NODE_ENV override survives dotenv-expand's no-override default
if (parsed.NODE_ENV) { processEnv.NODE_ENV = parsed.NODE_ENV; }
expand({ parsed, processEnv });

// public vars emitted under BOTH global namespaces, values JSON-stringified for DefinePlugin
if (prefixes.some(p => key.startsWith(p))) {
  publicVars[`import.meta.env.${key}`] = JSON.stringify(val);
  publicVars[`process.env.${key}`] = JSON.stringify(val);
}
```
```ts
// cleanup: only remove keys whose current value still equals what we parsed; NODE_ENV exempt
const cleanup = () => {
  if (cleaned) return;                       // idempotent latch
  for (const key of Object.keys(parsed)) {
    if (key === 'NODE_ENV') continue;        // comment: otherwise .env.${mode} won't load next time
    if (processEnv[key] === parsed[key]) delete processEnv[key];
  }
  cleaned = true;
};
```
```ts
// validatePrefixes throws BEFORE any file IO:
// '' would make EVERY env var public → inlined into client code through process.env.*/import.meta.env.*
```

**Flow:** mode defaults to `getNodeEnv()`; `mode === 'local'` throws early (`.env.local` reserved as temporary local file). The vendored dotenv `parse` normalizes CRLF, strips `export `, handles single/double/backtick quotes, expands `\n`/`\r` only inside double quotes, trims inline `#` comments. After expansion, only prefix-matching keys of the TARGET processEnv become define pairs. Cleanup is registered by `createRsbuild` onto both close hooks (`onCloseBuild` + `onCloseDevServer`).

**Invariant:** cleanup must compare against parsed values (not delete blindly) so user-set or externally-injected variables survive; idempotency latch prevents double-delete when both close hooks fire.

**Probe:** `e2e/cases/javascript-api/load-env/index.test.ts:17-55` pins parse map, dual-namespace publicVars with JSON quoting (`'"18"'`), rawPublicVars, and post-cleanup `process.env.REACT_NAME === undefined`; `:57-72` pins processEnv-target isolation; `:74-84` pins empty-prefix and whitespace-prefix throws. `e2e/cases/javascript-api/load-env-expand/index.test.ts:5-27` pins dotenv-expand composition (`PUBLIC_COMPOSED: 'rsbuild@1'`) and that existing target values win over expansion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "loadEnv validatePrefixes publicVars cleanup DOTENV_LINE", limit: 10 });
```

## Verdict
Adopt precedence ladder, dual-namespace define emission, value-equality cleanup, and the empty-prefix hard throw. Adapt prefix defaults to host conventions. Omit rsbuild's vendored regex micro-detail unless porting parsing itself. Coverage caveat: probes are e2e-level (Playwright-free assertions here) verified on-disk.
