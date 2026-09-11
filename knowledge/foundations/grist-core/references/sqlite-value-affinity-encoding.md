<!-- capsule-v2 -->
# Affinity-safe value encoding — how do you store a dynamic-typed value layer on SQLite without type affinity silently corrupting values?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When every cell can hold number/string/bool/list/blob regardless of its column's declared type, how do you prevent SQLite's NUMERIC/INTEGER/TEXT affinity from casting stored values behind your back?

## Encode decision table keyed on (value kind, column affinity)
**Path/Symbol:** `app/server/lib/DocStorage.ts:DocStorage._encodeValue` (:487–551), `_decodeValue` (:558–579), `_encodeColumnsToRows` (:468–477), `_getSqlType` (:603–638), `_getAffinity` (:646–659).
**Signature:** `static _encodeValue(marshaller: marshal.Marshaller, gristType: string, sqlType: string, val: any): Uint8Array | string | number | boolean | null`.
**Data Shape:** One shared `Marshaller({version: 2})` per batch (`_encodeColumnsToRows` unzips columns→rows first); returns SQLite-bindable scalars, JSON strings for list types, or marshalled BLOBs; `undefined` normalizes to `null`.

### Decisive source
```ts
case "string":
  if (affinity === "TEXT" || affinity === "BLOB") { return val; }
  // INTEGER/NUMERIC/REAL affinity casts strings that look like numbers
  // (vdbe.c:applyNumericAffinity). Anything NOT starting with [-+ space digit .]
  // is certainly safe; everything else is marshalled instead of risked.
  if (!/[-+ \t\n\r\v0-9.]/.test(val.charAt(0))) { return val; }
  return marshalled();
case "number":
  // TEXT affinity can't hold a bare number; NaN/-0/bool-ish ints in BOOLEAN
  // columns have lossy representations — marshal those too.
  if (affinity === "TEXT" || Number.isNaN(val) || Object.is(val, -0.0) ||
    (sqlType === "BOOLEAN" && (val === 0 || val === 1))) {
    return marshalled();
  }
  return val;
case "boolean":
  // Booleans only survive as booleans in BOOLEAN-typed columns; anywhere else
  // they'd collapse into 0/1, so wrap them.
  return (sqlType === "BOOLEAN") ? val : marshalled();
```

**Flow:** ChoiceList/RefList values → JSON string of `val.slice(1)` (Grist's `["L", ...]` wrapper dropped, plain JSON array stored) → arrays/Uint8Array/Buffer → marshalled BLOB → `null`/`undefined` → `null` → otherwise the affinity switch above. Decode is the exact inverse (`_decodeValue`): BLOB → `marshal.loads`; `Bool` column 0/1 → `Boolean`; list-type column string starting `[` → `["L", ...JSON.parse(val)]` (parse failure falls through raw).
**Invariant:** Ambiguous values NEVER reach SQLite bare — anything affinity could recast (numeric-looking strings into NUMERIC columns, booleans outside BOOLEAN columns, NaN/-0) is wrapped as a marshalled BLOB first, so stored bytes round-trip identically through any column-type change. Decode keys off the column's CURRENT type, so old marshalled blobs stay intact until explicitly converted (see sqlite-online-schema-alter's opportunistic sweep).
**Probe:** `test/server/lib/DocStorage.js` `.fetchTable` `"Should return same data as was stored into the table"` (:363) — round-trips tricky values incl. numeric-looking strings; `.ModifyColumn` test (:557+) asserts `Int` values are NOT converted to Text and text-y numbers stay marshalled.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_encodeValue _decodeValue _getAffinity _getSqlType", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the (value-kind × column-affinity) decision table verbatim for any dynamic-typed layer over SQLite — it is the complete answer to "why did my string '13' become integer 13". Adapt the marshaller to your host's canonical binary envelope (the requirement is: decidable BLOB-vs-native at both ends, versioned envelope). Omit Grist's ChoiceList/RefList JSON special cases unless you share the obj-code vocabulary; keep the principle that list-ish values get ONE textual encoding with the wrapper stripped.
