<!-- capsule-v2 -->
# Backend daemon platform matrix — how does a thin client pin a remote backend across OS/arch without shipping it?

**Source:** JetBrains Fleet install `air` 262.132.35 (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-air` (`lib/app/bootstrap/ship.json`, `dockMetadata.json`: no_recorded_issue / metadata_match). **Question:** When half your product lives on another machine (the workspace backend), what contract keeps client and daemon compatible?

## Connected graph-selected seam
**Path/Symbol:** `lib/app/bootstrap/ship.json` `meta` block + `lib/app/bootstrap/dockMetadata.json`.
**Signature:** `meta["fsd-archives-<os>_<arch>"] = "{\"type\":\"Remote\",\"url\":…fleet-parts/fsdaemon/<os>_<arch>/fsdaemon-262.132.35.zip…,\"hash\":…}"` for {linux,macos,windows}×{x64,aarch64}; `dockMetadata = {"apiVersion": <sha256>, "jbrVersion": "25.0.2-329.111", "minimumFleetSdkGradlePluginVersion": "0.6.250"}`.
**Data Shape:** the backend (`fsdaemon` — the payload also present at install time as `resources/jetbrainsd.tar.gz`) is declared per-platform as six pinned Remote coordinates inside SHIP's signed meta — NOT as loose files per platform in one universal archive. `apiVersion` is a content hash, and the SAME value appears as `dockApiVersion` in ship.json meta: a two-file equality join binding dock UI ↔ daemon API.

### Decisive source
```json
// ship.json meta (abridged)
"buildDate": "1786060800", "expirationDate": "1791244800",
"dockApiVersion": "ac90382a7e51e21c7494dd9ccfa32f6de156fc4da40a3de799020b12f9f35da7",
"fsd-archives-linux_x64":   "{...url:\"https://plugins.jetbrains.com/fleet-parts/fsdaemon/linux_x64/fsdaemon-262.132.35.zip\", hash:\"2246309c28b4...\"}",
"fsd-archives-windows_aarch64": "{...hash:\"5379874b7c65...\"}",  // 6 entries total
// dockMetadata.json (complete file)
{"apiVersion": "ac90382a7e51e21c7494dd9ccfa32f6de156fc4da40a3de799020b12f9f35da7",
 "jbrVersion": "25.0.2-329.111", "minimumFleetSdkGradlePluginVersion": "0.6.250"}
```

**Flow:** client resolves its `<os>_<arch>` → downloads the pinned fsdaemon zip (verifying sha256) for the REMOTE host or unpacks the bundled tarball → before connecting, checks the daemon reports the same `apiVersion` hash as dockMetadata declares → version-skew or missing platform entry = refuse to attach, not degrade.
**Invariant:** compatibility is CONTENT equality (the apiVersion hash), not a version-number comparison — either side regenerated against a different API surface breaks the join loudly; and the matrix must enumerate all six platforms up front because a missing key means that platform cannot get a backend at all.
**Probe:** from install root: `python3 -c "import json;m=json.load(open('lib/app/bootstrap/ship.json'))['meta'];ks=[k for k in m if k.startswith('fsd-')];print(len(ks), sorted(ks))"` → `6 [fsd-archives-linux_aarch64, linux_x64, macos_aarch64, macos_x64, windows_aarch64, windows_x64]`; `python3 -c "import json;a=json.load(open('lib/app/bootstrap/ship.json'))['meta']['dockApiVersion'];b=json.load(open('lib/app/bootstrap/dockMetadata.json'))['apiVersion'];print(a==b)"` → `True`; `ls resources/` → `jetbrainsd.tar.gz` present alongside.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.lib.app.bootstrap.dockMetadata.apiVersion" });
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "Variable", file_pattern: "dockMetadata", detail: "ids", limit: 5 });
```

## Verdict
Adopt: per-platform pinned Remote coordinates for remote components + content-hash API equality as the attach gate; declare the platform matrix exhaustively. Adapt: your transport (ssh/docker/local) around the same gate. Omit: fsdaemon internals and the jetbrainsd tarball layout (next-pass target). Companion seams: fleet-bundle-catalog-signed-manifests (SHIP meta authenticity), fleet-content-addressed-parts-layers (same hash discipline locally).
