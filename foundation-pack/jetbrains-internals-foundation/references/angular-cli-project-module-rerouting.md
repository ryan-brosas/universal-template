<!-- capsule-v2 -->
# Angular CLI project-module rerouting — how does the IDE run schematics with the PROJECT'S OWN @angular/cli across breaking CLI majors?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## argv splice + Module._resolveLookupPaths patch + per-major provider ladder
**Path/Symbol:** `plugins/angular-plugin/ngCli/generate.js` (:5-8); `plugins/angular-plugin/ngCli/rerouteModulesToProject.js`:`rerouteModulesToProject` (:6-22; twin in `runner.js` :10-26 per graph trace); `plugins/angular-plugin/ngCli/schematicsProvider90.js` (:6-54; siblings schematicsProvider{60,62,70,80}.js).
**Signature:** `node generate.js <projectLocation> <normal CLI args…>`; `rerouteModulesToProject(projectLocation: string, modulePrefixes: string[])`; provider exports a promise resolving to `{ getCollection, listSchematics, getSchematic, getDefaultSchematicCollection }`.
**Data Shape:** rerouted prefixes = `["@angular/cli", "@angular-devkit/core", "@angular-devkit/schematics", "rxjs"]` — resolved ONLY from `<projectLocation>/node_modules`.

### Decisive source
\`\`\`js
// generate.js — the project path rides argv[2] and is REMOVED so the real CLI sees clean argv:
const projectLocation = process.argv[2];
process.argv.splice(2, 1);
rerouteModulesToProject(projectLocation, ["@angular/cli", "@angular-devkit/core", "@angular-devkit/schematics", "rxjs"]);
require("./generateVirtual");

// rerouteModulesToProject.js — patch Node's lookup paths, handling BOTH return shapes:
Module._resolveLookupPaths = function _resolveLookupPaths(request, parent, newReturn) {
    const result = oldResolveLookupPaths(request, parent, newReturn);
    for (const prefix of modulePrefixes) {
        if (request.startsWith(prefix)) {
            const projectNodeModules = path.resolve(projectLocation, "node_modules");
            return newReturn || result.length > 2 || (result.length === 2 && !Array.isArray(result[1]))
                ? [projectNodeModules]
                : [result[0], [projectNodeModules]];
        }
    }
    return result;
};

// schematicsProvider90.js — workspace API branch across CLI majors:
if (getWorkspaceDetails) { return await getWorkspaceDetails(); }        // Angular 9-10
const workspaceFile = project_1.findWorkspaceFile();                     // Angular 11+
if (workspaceFile === null) { const [, localPath] = config_1.getWorkspaceRaw('local');
  if (localPath !== null) throw new Error(`An invalid configuration file was found ['${localPath}'].` …); }
…
let { listSchematicNames } = (await command.createWorkflow({ interactive: false })).engineHost;
\`\`\`

**Flow:** JVM selects the provider file matching the project's detected CLI major → generate.js splices argv and installs the lookup patch → subsequent requires of the four prefixes resolve from the project → generateVirtual builds the SchematicCommand with the loaded workspace → engineHost exposes collection/schematic listing to the IDE.
**Invariant:** (1) the patch must preserve the legacy AND modern `_resolveLookupPaths` contract (the `newReturn / result.length / isArray` dance) or every require in the process breaks; (2) prefix matching is startsWith on the REQUEST string — order matters only vs other patches; (3) workspace loading branches by CLI major with an explicit error when a local workspace file exists but is invalid; (4) never let the IDE's bundled CLI shadow the project's — that is the entire reason for the patch.
**Probe:** `node --check` on generate.js, rerouteModulesToProject.js, schematicsProvider90.js → all OK (executed). Coverage: all three no_recorded_issue. Live schematic execution needs an Angular project host (caveat).

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "rerouteModulesToProject", limit: 5 });
// hits: ngCli/rerouteModulesToProject.rerouteModulesToProject :6-22, ._resolveLookupPaths :9-21,
//       ngCli/runner.rerouteModulesToProject :10-26 (same patch reused by the runner entry)
\`\`\`

## Verdict
Adopt the three-part shape (argv side-channel, targeted lookup-path patch over an explicit prefix allow-list, per-major adapter modules) whenever you must execute the USER's copy of a versioned tool in-process. Adapt the prefix list and provider selection to your tool. Omit Angular-specific workspace error strings; keep the invalid-local-file explicit-throw behavior.
