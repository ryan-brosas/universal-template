<!-- capsule-v2 -->
# process.env define leak guard — why does the check JSON.parse stringified defines and compare against live process.env?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the builtin import.meta.env surface and the env-leak warning before DefinePlugin registration.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/define.ts` — `checkProcessEnvSecurity` 7–47, builtinVars 59–70, merge 72, plugin registration 76.
**Signature:** `checkProcessEnvSecurity(define: DefinePluginOptions, logger): void`.
**Data Shape:** define keys are dot-paths ('process.env.BASE_URL'); values are raw or JSON-stringified objects (DefinePlugin semantics).

### Decisive source
```ts
const pathKey = Object.keys(value).find(
  // Windows uses `Path`, other platforms use `PATH`
  (key) => key.toLowerCase() === 'path' && value[key] === process.env[key],
);
```
```ts
// Check `{ 'process.env': process.env }`
if (typeof value === 'object') { check(value); return; }
// Check `{ 'process.env': JSON.stringify(process.env) }`
if (typeof value === 'string') { try { check(JSON.parse(value)); } catch { /* ignore */ } }
```

**Flow:** builtins expose MODE/DEV/PROD/SSR/BASE_URL/ASSET_PREFIX under `import.meta.env` plus BASE_URL/ASSET_PREFIX on process.env; user source.define spreads OVER them. The security check fires only when the WHOLE env object is assigned under 'process.env' AND a Path/PATH entry still equals the live value — proving real env was captured rather than a curated subset. Both object form and stringified form detected; parse failures ignored silently.
**Invariant:** (1) comparison must be by VALUE equality with process.env[key] — a user who deliberately redefines PATH to a literal would not match and gets no false warning; (2) the check runs BEFORE chain registration so the warning appears once at config time, not per rebuild; (3) JSON.parse of non-JSON strings must be swallowed — many defines are plain literals.
**Probe:** unit snapshot `packages/core/tests/define.test.ts:6` (DefinePlugin registration shape); e2e define cases under `cases/config`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginDefine checkProcessEnvSecurity builtinVars", limit: 8 });
```

## Verdict
Adopt the two-form leak probe with case-insensitive PATH detection and the import.meta.env builtin set. Adapt variable names to host conventions. Omit SSR flag if host has no server target.
