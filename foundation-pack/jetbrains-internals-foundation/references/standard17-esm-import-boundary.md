<!-- capsule-v2 -->
# ESM-only linter boundary — how does a CommonJS shim call `eslint-config-standard` v17 when the package became ESM-only?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Dynamic import() with Windows drive conversion
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/standard17-plugin.js`:`Standard17Plugin.invokeESLint` (:111-131); class head :43-46.
**Signature:** `invokeESLint(args, additionalOptions?) -> Promise<Linter results>`; ctor state carries ONLY `{ includeSourceText, standardPackagePath }` — no eslint paths at all.
**Data Shape:** engine obtained as `(await import(path)).default` (standard v17's default export); options = `{ filename: args.fileName, fix?: true }`.

### Decisive source
```js
options.filename = requestArguments.fileName;
path = this.standardPackagePath + "/index.js";
if (path.charAt(1) == ":") {
  // Windows absolute path
  path = "file:///" + path;
}
standardEngine = (await import(path))["default"];
return standardEngine.lintText(requestArguments.content, options);   // v16 was lintTextSync; v17 returns a Promise
```

**Flow:** per request build an absolute entry path into the USER's standard install → convert bare Windows drive paths to file URLs so `import()` accepts them → dynamic import (the only way a CJS module loads an ESM-only package) → take `.default` → await async lintText and pass the result straight through the shared response envelope after source-stripping.
**Invariant:** (1) ALL gates the legacy hybrid had are GONE here by design — no ignore check (that lived in ESLint), no FileKind acceptance gating; standard v17's config IS the authority for both, so re-implementing them would fight the tool; (2) sync→async migration is absorbed inside the plugin (`onMessage` was already await-based), keeping the wire envelope byte-compatible with the other two generations; (3) the drive-letter probe tests `charAt(1) == ":"` and must run BEFORE import or Windows hosts throw ERR_UNSUPPORTED_ESM_URL_SCHEME.
**Probe:** `node --check standard17-plugin.js` → OK; `grep -c "file:///"` = 1, `grep -c lintTextSync` = 0 in this file vs 1 in legacy (executed). Coverage: no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", name_pattern: "^Standard17Plugin$", limit: 5 });
// hit: bin.standard17-plugin.Standard17Plugin @ standard17-plugin.js:43-46, single caller eslint-plugin-provider:1
```

## Verdict
Adopt dynamic-import-with-file-URL-fix as THE pattern for CJS hosts consuming ESM-only tooling; keep a state object that carries only what this generation actually needs. Adapt the URL conversion to your platform matrix (POSIX needs nothing). Omit re-implemented ignore/kind gates when the target tool already owns that policy — duplicating policy across generations is how shims rot.
