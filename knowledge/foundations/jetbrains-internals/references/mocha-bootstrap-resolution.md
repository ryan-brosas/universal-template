<!-- capsule-v2 -->
# Mocha bootstrap resolution + JB_VERBOSE persona — how does the reporter load mocha's OWN internals across install layouts, and switch console personas?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (mocha-intellij lib, cluster-identical); Codebase Memory `jetbrains-webstorm`. **Question:** The reporter must require `mocha/lib/reporters/base` from INSIDE the user's project — how does it find the right mocha when the entry point is a wrapper, a monorepo, or Yarn PnP?

## Package-root walk + inner-dependency fallback
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijUtil.js` — `requireMochaModule` (:174-196), `findPackageDir` (:234-253, walk UP until `path.basename(dir)==='node_modules'`, testing `require.resolve(<dir>/package.json)` at each step), `findMochaInnerDependency` (:217-226, `require.resolve('mocha', {paths:[packageDir]})` then cut at LAST `/mocha/`), `getContextRequire` (:203-211, `module.createRequire(process.cwd())` when available — explicitly for Yarn PnP), `requireBaseReporter` (:262-274: `JB_VERBOSE=true|1` swaps base.js → spec.js so stats still populate while console shows spec output).
**Signature:** `requireMochaModule(mochaModuleRelativePath: string): module`; `maybeOpenSocket(): ?net.Socket`.
**Data Shape:** resolution order: package root of `require.main.filename` → if that dir is literally named `mocha`, direct join → else try join, on failure resolve inner mocha dependency. Transport: env `JB_TEAMCITY_SOCKET_PATH` (unix socket) or `JB_TEAMCITY_SOCKET_PORT` (+ optional HOST) opens a socket; otherwise stdout; socket gets `unref()` + `setNoDelay(true)`, destroyed on 'error'/'exit'/'SIGINT' (with process.exit in SIGINT).

### Decisive source
```js
function findPackageDir(startDir) {
  let dir = startDir;
  while (dir != null) {
    if (path.basename(dir) === 'node_modules') break;
    try {
      const packageJson = path.join(dir, 'package.json');
      require.resolve(packageJson, {paths: [process.cwd()]});
      return dir;
    } catch (e) {}
    const parent = path.dirname(dir);
    if (dir === parent) break;
    dir = parent;
  }
  return null;
}
const JB_VERBOSE = ['true','1'].includes((process.env.JB_VERBOSE || '').toLowerCase());
const baseReporterPath = JB_VERBOSE ? './lib/reporters/spec.js' : './lib/reporters/base.js';
```

**Flow:** reporter constructor → requireBaseReporter (persona-selected path, tolerant: warn+undefined on failure, `inherits` skipped when absent) → maybeOpenSocket (transport decision, null = stdout) → runner handlers use `util.safeFn` wrapper so ANY handler exception degrades to a stderr warning instead of killing the test run.
**Invariant:** Base-reporter load failure is NON-FATAL (stats/growl lost, TeamCity stream unaffected) but wrong-mocha resolution IS fatal-by-design (loud Error naming the failing path). Wrong port: resolving mocha via the reporter's own module paths instead of `require.main`'s package root (picks the WRONG copy under hoisted monorepos); forgetting `unref()` (socket keeps process alive after tests end).
**Probe:** deterministic source pins executed against shipped file: `grep -c "createRequire" → 2`, `'./lib/reporters/spec.js'` present only behind JB_VERBOSE; behavior battery `/tmp/jb-p7/probe-v3.js` exercises escape/joinList/safeFn-adjacent exports of this same module.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "requireMochaModule findPackageDir", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt main-entry-relative package walk with inner-mocha fallback for any tool injected beside an unknown dependency version. Adapt the persona env var name. Omit PnP branch if your host has no Yarn PnP.
