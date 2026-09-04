<!-- capsule-v2 -->
# Fleet content-addressed parts store — how are plugin payloads cached, verified, and split across processes?

**Source:** JetBrains Fleet install `air` 262.132.35 (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-air` (`lib/app/code-cache/*/parts.json`: no_recorded_issue / metadata_match). **Question:** How does one install serve frontend, backend-workspace, and dock processes from a shared artifact set without a plugins/ directory?

## Connected graph-selected seam
**Path/Symbol:** `lib/app/code-cache/<sha256>/parts.json` — 104 manifests inside 871 content-addressed dirs (e.g. `a378a0001dca.../parts.json`, the `fleet.stylelint` bundle).
**Signature:** `{"layers": {"common"? | "frontend"? | "workspace"? | "dock"?: {"modulePath": [{"coordinates": Coordinates, "serializedModuleDescriptor": base64}], "modules": [String], "resources": [Coordinates]}}}`.
**Data Shape:** dir name == the sha256 `hash` of the catalog Coordinate that fetched it (fleet.ai `partsCoordinates.hash` `aee80a39ef5f…` → that exact dir). Dirs hold EITHER one payload artifact named by the coordinate (`fleet.plugins.stylelint.common.jar`, `frontend.zip`, `keymap.zip`) OR a parts.json manifest. Key vocabulary over all 871 caches: `meta`×654, `coordinates`×587, `layers`×104, `frontend`×101, `common`×58, `workspace`×51, `dock`×1.

### Decisive source
```json
// lib/app/code-cache/a378a0001dca1c0fd8f9c760a593d57cf500c6e698f205057cf2486546ea43b2/parts.json (abridged)
{"layers": {
  "common":   {"modulePath": [{"coordinates": {"type": "Remote", "url": ".../fleet%2Eplugins%2Estylelint%2Ecommon%2Ejar", "hash": "cb4330af47dc...", "meta": {}},
               "serializedModuleDescriptor": "yv66vgAAAEEADQEAC21vZHVsZS1pbmZvBwAB..."}], "modules": [], "resources": []},
  "frontend": {"modulePath": [{"coordinates": {..."hash": "09a81ab78e76..."}, "serializedModuleDescriptor": "yv66vgAAAE..."}],
               "modules": ["fleet.plugins.stylelint.frontend"],
               "resources": [{"type": "Remote", "url": ".../module=frontend%2Ezip", "hash": "35de6f00d38a..."}]},
  "workspace": {"modulePath": [...], "modules": ["fleet.plugins.stylelint.workspace"], "resources": []}}}
```
The `serializedModuleDescriptor` base64-decodes to a JVM class file (`yv66vg` magic): a compiled JPMS `module-info.class` naming e.g. module `fleet.plugins.stylelint.frontend` — module identity travels INLINE with every artifact, not as side metadata.

**Flow:** catalog entry references `partsCoordinates` → client fetches parts.json into `code-cache/<its hash>/` → each layer's `modulePath` coordinates fetch jar payloads into their own hash dirs → layers compose per process role (thin frontend loads `frontend`, backend loads `workspace`, both share `common`; the dock app has its own layer) → every artifact is hash-verified against its coordinate on arrival.
**Invariant:** content addressing is the ONLY linkage — no path or name ever identifies an artifact; two bundles sharing a dependency jar share one cache dir automatically, and mutating any payload breaks exactly the entries whose coordinates pin it.
**Probe:** from install root: `ls lib/app/code-cache | wc -l` → `871`; `grep -h -o '"[a-zA-Z]*": {' lib/app/code-cache/*/parts.json | sort | uniq -c | sort -rn | head -7` → counts above; base64-decoding a layer's `serializedModuleDescriptor` and hex-dumping gives `000000 ca fe ba be ...` (JVM class magic, minor 0x41 = Java 21 module-info).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "Variable", file_pattern: "code-cache", detail: "ids", limit: 25 });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.lib.app.code-cache.a378a0001dca1c0fd8f9c760a593d57cf500c6e698f205057cf2486546ea43b2.parts.common" });
```

## Verdict
Adopt: content-addressed artifact store + per-bundle layer manifests with embedded JPMS descriptors — kills duplicate dependencies and makes verification local to each artifact. Adapt: your process topology names for the layer split; your fetch/verify loop. Omit: JetBrains marketplace URLs and signature trust chain. Companion seams: fleet-bundle-catalog-signed-manifests (who references these hashes), thin-vs-full-layout-taxonomy (why air lacks plugins/).
