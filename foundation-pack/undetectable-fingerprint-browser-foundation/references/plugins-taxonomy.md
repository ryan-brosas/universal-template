<!-- capsule-v2 -->
# Plugins taxonomy — four buckets, a canonical PDF quintet, and name-keyed ref-hash stability

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** What must `navigator.plugins` (and its `mimeTypes` mirror) look like so plugin-enumeration detectors see a coherent modern-Chromium identity?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.plugins[]` — TOP LEVEL of each record, always an array (10,000/10,000). The `navigator{}` object has NO `plugins` key (its 13-key surface: app_codename, app_name, app_version, brands, full_version, full_version_list?, pdf_viewer_enabled, platform, product, product_sub, user_agent, vendor, vendor_sub). Graph caveat: `not_tracked` binary artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `Plugin = {name: string, file_name: string, description: string, ref: int32, mimes: int32[]}` — `ref` and mime entries are integer hashes into product-private tables.

## Data Shape
Four buckets partition the corpus exactly:
- **canonical5 ×9410** — `["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer", "Microsoft Edge PDF Viewer", "WebKit built-in PDF"]`, all `file_name: "internal-pdf-viewer"`, description `"Portable Document Format"`.
- **empty [] ×55** — the empty-plugins cohort is itself detector-visible.
- **Native-Client legacy ×59** (executed `any(.name=="Native Client")`) — signature groups `{Chrome PDF Plugin | Chrome PDF Viewer | Native Client}×47 + {Chromium PDF Plugin | Chromium PDF Viewer | Native Client}×9 + {Microsoft Edge PDF Plugin | Microsoft Edge PDF Viewer | Native Client}×3`.
- **randomized long tail ×476 across 358 total distinct name signatures** (fresh count) — includes non-NaCl legacy pairs (`{Chrome PDF Plugin | Chrome PDF Viewer}×42`, `{Chromium PDF Plugin | Chromium PDF Viewer}×12`) and oddballs: Shockwave Flash + Ruffle stacks ×5 records, THREE of which duplicate the name `"Shockwave Flash"` twice in one array.
- Within canonical5, the five `ref` hashes `[1446158656, 1010824838, -1972253206, -545395695, 1114102244]` and mimes pair `[-1248334925, -1004735216]` are BYTE-STABLE across all 9410 records (fresh unique-count probe returned exactly 1 distinct quintet): `ref` is a NAME-KEYED hash constant. The legacy Chrome family reuses `1010824838` (Chrome PDF Viewer's ref) beside its own `842281895/-1466093580`; Chromium family reuses `-1972253206`.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
buckets : {"canon5":9410,"empty":55,"nacl":59}
refs    : canonical5 map(.ref) -> unique | length == 1     // byte-stable quintet
flash   : 5 records; dup-name flash records: 3
sigs    : 358 distinct "|"-joined name signatures
```

**Flow:** choose cohort by record (never synthesize) → emit `.plugins[]` verbatim with hashed refs/mimes → keep `pdf_viewer_enabled` consistent (it is `false` on only 54/10000 records — see navigator-scalar-cohorts).
**Invariant:** plugin names, order, and ref/mime hash values move TOGETHER as captured units. A porter who renames one entry or recomputes refs breaks the name-keyed hash relation that all 9410 canonical records share. Empty plugins and duplicated Flash names are real cohorts — do not "repair" them.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{"canon5":[.[]|select((.plugins|length)==5 and .plugins[0].name=="PDF Viewer" and .plugins[1].name=="Chrome PDF Viewer" and .plugins[4].name=="WebKit built-in PDF")]|length,"empty":[.[]|select((.plugins|length)==0)]|length,"nacl":[.[]|select(any(.plugins[];.name=="Native Client"))]|length}'` → `{"canon5":9410,"empty":55,"nacl":59}` (executed pass 7); and `xz -dc ... | jq -c '[.[]|select((.plugins|length)==5 and .plugins[0].name=="PDF Viewer")|.plugins|map(.ref)] | unique | length'` → `1` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "navigator plugins PDF Viewer Native Client plugin ref hash mime" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt the four-bucket taxonomy and the name-keyed ref-hash constants; adapt the storage layout freely; omit inventing new plugin entries or re-hashing refs. Caveats: resolver tables for the int refs ship with the closed binary — mapping beyond the recorded name↔ref pairs is unverified at pin.
