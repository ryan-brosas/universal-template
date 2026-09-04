<!-- capsule-v2 -->
# Context-require substrate — how does a bundled shim require modules from the PROJECT's module graph (Yarn PnP included) instead of its own?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## createRequire ladder inside eslint-common
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint-common.js`:`getContextRequire(contextPath)` (:32-50, module-PRIVATE); public surface `requireInContext` (:22-25) / `requireResolveInContext` (:27-30); helpers `normalizePath` (:8-16) / `toUnixPathSeparators` (:18-20).
**Signature:** `requireInContext(modulePath, contextPath) -> exports`; `requireResolveInContext(modulePath, contextPath) -> absolute path`; `normalizePath(p) -> p guaranteed trailing '/' + unix separators (undefined passthrough)`.
**Data Shape:** `contextPath` = the USER project's package.json path sent by the JVM side; `null` means "use the shim's own bare require".

### Decisive source
```js
function getContextRequire(contextPath) {
  if (contextPath != null) {
    var module = require('module');
    if (typeof module.createRequire === 'function') {
      // Implemented in Yarn PnP: https://next.yarnpkg.com/advanced/pnpapi/#requiremodule
      return module.createRequire(contextPath);
    }
    if (typeof module.createRequireFromPath === 'function') {
      // deprecated createRequireFromPath … to support Node.js 10.x
      return module.createRequireFromPath(contextPath);
    }
    throw Error('Function module.createRequire is unavailable in Node.js ' + process.version +
                ', Node.js >= 12.2.0 is required');
  }
  return require;
}
```

**Flow:** every plugin constructor resolves the USER's eslint/standard entry through `requireInContext(path, state.packageJsonPath)` → resolution honors the project's own node_modules/.pnp.cjs instead of the IDE-bundled tree → `normalizePath` guarantees a trailing slash so subsequent `+ "lib/options"` concatenations stay valid cross-platform.
**Invariant:** (1) `getContextRequire` is intentionally NOT exported — callers can only go through the two wrappers (verified by live execution: `Object.keys(require('eslint-common.js'))` = containsString, normalizePath, requireInContext, requireResolveInContext, toUnixPathSeparators); (2) the ladder order matters: modern API first, DEPRECATED fallback second with its Node-10 rationale in-source, then a hard throw that NAMES the minimum Node version rather than failing obscurely later.
**Probe:** executed this run against the real distribution: `requireInContext("./eslint-api.js", <shim path>)` loaded the bundled eslint-api and returned `{ESLintResponse, FileKind, FixErrors, GetErrors}` with FileKind values `ts/html/vue/js_and_other`; missing module → `MODULE_NOT_FOUND`; `normalizePath("C:\\a\\b") == "C:/a/b/"`. Coverage: no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "getContextRequire requireInContext", limit: 6 });
// cluster: bin.eslint-common.getContextRequire :32-50 with requireInContext/requireResolveInContext CALLS edges
```

## Verdict
Adopt this exact three-rung ladder whenever a host process must execute the USER's copy of a tool (editors, LSP shims, CI helpers): context-relative require beats cwd tricks and works under PnP. Adapt the minimum-Node floor to your host. Omit the deprecated rung only below Node 10 support ceilings — and keep the descriptive hard-throw; silently falling back to the shim's own modules would lint with the WRONG installation.
