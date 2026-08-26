<!-- capsule-v2 -->
# Per-component third-party license manifests — how does a multi-binary distribution ship its license compliance?

**Source:** JetBrains Fleet install `air` 262.132.35 (proprietary distribution; manifests are factual metadata); Codebase Memory `jetbrains-air` (`license/*third-party-libraries.json`: no_recorded_issue / metadata_match). **Question:** At what granularity must license attribution be shipped when the product is a catalog of separately downloadable components?

## Connected graph-selected seam
**Path/Symbol:** `license/<component>-262.132.35-third-party-libraries.json` — 112 files: 107 under `license/fleet.<bundle>-…` (one per catalog bundle, incl. sub-bundles like `fleet.ai.agent.claude` and keymap packs `fleet.keymaps.Eclipse`), plus ROOT per-binary manifests for non-bundle executables (`fsdaemon-`, `launcher-`, `mcp-proxy-`, `printenv-`) and one aggregate `SHIP-262.132.35-third-party-libraries.json`.
**Signature:** flat array of `{name, version, url, license, licenseUrl}` — no nesting, no per-file hashes.
**Data Shape:** granularity = DEPLOYABLE COMPONENT, mirroring the download matrix: each marketplace-fetchable bundle gets its own manifest (so a user installing only some bundles can be shown only their attributions), while native binaries outside the bundle system get root-level manifests keyed by binary name.

### Decisive source
```json
// license/SHIP-262.132.35-third-party-libraries.json (head)
[{"name": "Guava", "version": "33.5.0-jre", "url": "https://github.com/google/guava",
  "license": "Apache 2.0", "licenseUrl": "https://github.com/google/guava/raw/master/LICENSE"},
 {"name": "JNA", "version": "5.17.0", ...},
 {"name": "JetBrains Annotations", "version": "26.0.2", ...},
 {"name": "Kotlin Coroutines for JDK 8", "version": "1.10.2-intellij-1", ...}]
// license/fleet.maven-262.132.35-third-party-libraries.json (tail) ends the same way:
"license": "MIT", "licenseUrl": "https://www.slf4j.org/license.html"
```
The SHIP aggregate lists the ship-layer's own deps (Guava, JNA, Kotlin stdlib/coroutines at `*-intellij-1` forks); each `fleet.*` manifest lists that feature's third-party set (e.g. `fleet.maven` → slf4j).

**Flow:** build tooling scans each component's dependency tree → emits one flat JSON per deployable component + an aggregate for the ship kernel → files ride the install unconditionally (they are data, not code) → UI/legal surfaces read exactly the manifests of components actually present or downloaded.
**Invariant:** manifest presence is tied to component identity, not to install contents — every downloadable part carries its attribution with it; adding a component without its `<component>-<build>-third-party-libraries.json` breaks the compliance contract, not just a display.
**Probe:** from install root: `ls license/*third-party-libraries.json | wc -l` → `112`; `ls license/*.json | grep -v fleet` → `fsdaemon-`, `launcher-`, `mcp-proxy-`, `printenv-`, `SHIP-…`; `python3 -c "import json;d=json.load(open('license/SHIP-262.132.35-third-party-libraries.json'));print(len(d), list(d[0].keys()))"` → count + `["name","version","url","license","licenseUrl"]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "Variable", file_pattern: "third-party-libraries", detail: "ids", limit: 25 });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.license.SHIP-262.132.35-third-party-libraries.json.__file__" });
```

## Verdict
Adopt: per-deployable-component flat SBOMs plus a named aggregate, filename-keyed by `<component>-<build>`; attribution travels with the artifact. Adapt: your schema fields and scan pipeline. Omit: JetBrains' scanning toolchain. Companion seams: fleet-bundle-catalog-signed-manifests (defines what a component is), broken-plugin-denylist-db (the other per-build shipped registry).
