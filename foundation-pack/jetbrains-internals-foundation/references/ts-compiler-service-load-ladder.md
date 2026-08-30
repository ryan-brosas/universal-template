<!-- capsule-v2 -->
# TypeScript compiler service load ladder — how do you load tsserver into your own Node process across TS4/TS5 layouts, Yarn PnP, and exports that lie?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Version-ordered require targets with vm-context last resort
**Path/Symbol:** `plugins/javascript-plugin/jsLanguageServicesImpl/typescript/service-loader.js`:`getService` (:9-28); helpers `loadWithYarnPnp` (:48-84), `loadWithRequire` (:108-142), `evaluateInContext` (:30-47), `getVersion` (:94-107).
**Signature:** `getService(state) -> { ts, serverFilePath }`, where `state = { serverFolderPath, packageJson }`.
**Data Shape:** input is the TypeScript lib folder path (trailing slash normalized) plus optional project package.json (for PnP). Output is the loaded compiler namespace + resolved file path. Failure shapes: thrown `Error('Service file is empty')` / `Error('Cannot find tsserverlibrary.js or tsserver.js file in …')`.

### Decisive source
\`\`\`js
// The target ORDER flips with the compiler major — this is the whole trick:
var tsVersion = getVersion(serviceFolderPathWithSlash, require);
var targets = tsVersion[0] >= 5 ? ["tsserver", "tsserverlibrary"] : ["tsserverlibrary", "tsserver"];
var fromRequire = loadWithRequire(serviceFolderPathWithSlash, targets);
if (fromRequire != null) return fromRequire;
return evaluateInContext(serviceFolderPathWithSlash, targets);

// getVersion: bundled-copy shortcut + parse-failure default:
if (serviceFolderPathWithSlash.endsWith("external/")) return [5];   // bundled version
…
return [4];                                                          // default on any error

// loadWithRequire: an export WITHOUT .version is not the API surface (TS 5.5 note):
if (!tsService.version) {
  // typescript 5.5 launches service from tsserver, but it doesn't export the api,
  // which is exported from tsserverlibrary.
  continue;
}
// and a missing sibling lib.d.ts means we resolved a wrapper — hop two dirs up to the REAL typescript:
if (!fs.existsSync(nodeModulesCandidate + "/typescript/lib/lib.d.ts")) { … }
else resolvePath = nodeModulesCandidate + "/typescript/lib/" + target + ".js";
\`\`\`

**Flow:** normalize folder → try Yarn PnP (`process.versions.pnp` + `module.createRequire`) if project metadata present → version-gated require loop over `lib/<target>.js` → validate `.version`, re-point to real package via `lib.d.ts` probe → final fallback reads the file text and evaluates it in a fresh vm context primed with module/require/process/Buffer globals, returning `context.ts`.
**Invariant:** never trust a successful require alone — validate the `.version` export; keep target order version-dependent (TS≥5 prefers `tsserver`, TS<5 must get `tsserverlibrary` first); PnP resolution must go through a createRequire rooted at the PROJECT's package.json, not the host's; vm evaluation is strictly last (it loses module caching).
**Probe:** `node --check service-loader.js` → OK (executed). Content pin: exact ternary at :22. Coverage: `check_index_coverage` → no_recorded_issue. Live execution of getService needs a real TypeScript checkout — recorded caveat.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "service-loader getService typescript", limit: 10 });
// rank-4 hit: jetbrains-webstorm.plugins.javascript-plugin.jsLanguageServicesImpl.typescript.service-loader.getService @ plugins/javascript-plugin/jsLanguageServicesImpl/typescript/service-loader.js:9-28
\`\`\`

## Verdict
Adopt the ladder (PnP → version-ordered require → vm fallback) and the `.version` validation as the port; it is the only ordering that survives TS 4→5 file renames and wrapper packages. Adapt the bundled shortcut (`external/` ⇒ major 5) to your own vendored-layout marker. Omit the IntelliJ logger wiring (`serverLogger`) and replace with your host's logging.
