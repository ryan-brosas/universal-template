<!-- capsule-v2 -->
# Fleet signed bundle catalog — how does a thin client declare its whole feature set without plugin.xml?

**Source:** JetBrains Fleet install `air` 262.132.35 (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-air` (`lib/app/bootstrap/bundles.json` + `ship.json`: no_recorded_issue / metadata_match). **Question:** Where does the thin client learn which features exist, which versions are compatible, and whether the manifest is trustworthy?

## Connected graph-selected seam
**Path/Symbol:** `lib/app/bootstrap/bundles.json` (top-level `{shipVersions, plugins[]}`, 103 plugin entries) and sibling `lib/app/bootstrap/ship.json` (the SHIP pseudo-bundle, same schema).
**Signature:** `entry = {id, version, dependencies: {bundleId -> version}, compatibleShipVersionRange: {from, to}, signature: <base64 PGP SIGNATURE>, meta}`.
**Data Shape:** every entry — including SHIP itself — shares ONE schema. `meta` carries `readableName`, `description`, `supportedProducts: "AIR"`, `vendor/vendorName`, remote `Coordinates` for icons and parts (`defaultIconCoordinates`/`darkIconCoordinates`/`partsCoordinates`). SHIP's meta adds `buildDate`/`expirationDate` (unix seconds; build 1786060800 → expiry 1791244800, ~60 days) and `dockApiVersion`.

### Decisive source
```json
// bundles.json entry fleet.ai (abridged)
{"id":"fleet.ai","version":"262.132.35",
 "dependencies":{"fleet.ai.auth":"262.132.35","fleet.code":"262.132.35","fleet.git":"262.132.35", "...":"..."},
 "compatibleShipVersionRange":{"from":"262.132.35","to":"999.8191.9999"},
 "signature":"LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0K...",
 "meta":{"partsCoordinates":"{\"type\":\"Remote\",\"url\":\"https://plugins.jetbrains.com/api/fleet/download?xmlId=fleet%2Eai&version=262%2E132%2E35&module=parts%2Ejson\",\"hash\":\"aee80a39ef5f...\"}",
         "readableName":"AI","supportedProducts":"AIR"}}
// ship.json header
{"formatVersion":0,"id":"SHIP","version":"262.132.35","dependencies":{},
 "compatibleShipVersionRange":{"from":"262.132.35","to":"999.8191.9999"},"signature":"LS0t..."}
```

**Flow:** boot reads the catalog → an entry is usable only if the running build ∈ `[shipVersions] ∩ compatibleShipVersionRange` → dependency map resolves transitively to exact pinned versions → each payload/icon/parts reference is fetched from its Coordinates and verified against the sha256 `hash` → the PGP signature authenticates the manifest BEFORE any code runs.
**Invariant:** the catalog is the ONLY feature registry — there is no plugin.xml plane in this install; deleting/altering one entry removes that capability without touching any other entry. Signatures cover entries individually, so a partial catalog update stays verifiable.
**Probe:** `python3 -c "import json;d=json.load(open('lib/app/bootstrap/bundles.json'));print(list(d.keys()),len(d['plugins']),list(d['plugins'][0].keys()))"` → `["shipVersions","plugins"] 103 ["id","version","dependencies","compatibleShipVersionRange","signature","meta"]`; `base64 -d <(python3 -c "import json;print(json.load(open('lib/app/bootstrap/ship.json'))['signature'])") | head -2` → `-----BEGIN PGP SIGNATURE-----`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "Variable", file_pattern: "bundles.json", detail: "ids", limit: 25 });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.lib.app.bootstrap.bundles.fleet.ai" });
```

## Verdict
Adopt: single-schema, per-entry-signed versioned catalog as the feature registry; range-gated compatibility with transitive exact-version dependencies. Adapt: your signing infrastructure and marketplace URL scheme. Omit: JetBrains' PGP key hierarchy and marketplace API internals (not shipped). Caveat: signature VERIFICATION path is client-side code not shipped here — the artifact proves signatures exist, not the trust chain. Companion seams: fleet-content-addressed-parts-layers (payload store), fleet-dock-modulepath-layer-lists (dock boot).
