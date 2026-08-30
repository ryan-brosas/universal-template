<!-- capsule-v2 -->
# SQLite EntityMap — why does a 2,862-line importer keep its id mappings in an in-memory SQLite table instead of a Map, and how do the key encodings work?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does the schema-mapping store give the Airtable import that a plain object can't?

## in-memory sqlite mapping with JSON:: tagged values
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/EntityMap.ts:EntityMap/DBStream` (whole file).
**Signature:** `new EntityMap(...cols)`; `init()` (must await — lazy db promise); `addRow(row)`; `getRow(col, val, res?): Promise<row>`; `getCount()`; `getStream(res?): DBStream`; `getLimit(limit, offset)`.
**Data Shape:** single `mapping` table; constructor cols become `TEXT` columns; objects serialized as `'JSON::' + JSON.stringify(...)` and decoded on read.

### Decisive source
```ts
this.db = new Promise((resolve, reject) => {
  const db = new sqlite3.Database(':memory:');
  const colStatement = this.cols.length > 0 ? this.cols.join(' TEXT, ') + ' TEXT' : 'mappingPlaceholder TEXT';
  db.run(`CREATE TABLE mapping (${colStatement})`, ...);
});
async addRow(row) {
  ...
  for (const col of cols.filter((col) => !this.cols.includes(col))) {
    promises.push(new Promise((resolve, reject) => {
      this.db.run(`ALTER TABLE mapping ADD '${col}' TEXT;`, ...)   // late columns allowed
    }));
  }
  const values = Object.values(row).map((val) =>
    typeof val === 'object' ? `JSON::${JSON.stringify(val)}` : val);
```

**Flow:** the import creates one map (`aTblId → ncId/ncName/ncParent`), then thousands of async helpers query it by column value. Late-discovered attributes ALTER-TABLE themselves in. `getStream()` walks rows one-at-a-time via prepared statement — used to replay mappings for later phases.
**Invariant:** keys are case-folded by encoding: uppercase letters become `_X` (and `'` doubled) because SQLite identifiers/columns were treated case-insensitively in their workflow; reads reverse it. Object values MUST round-trip through the `JSON::` tag — a bare object would be stored as `[object Object]`. `init()` is mandatory before any row op (throws string 'Please initialize first!').
**Probe:** no unit test upstream. Source-grounded probe: `EntityMap.ts:200-223` — processResponseRow/processKey/revertKey trio; `:56-69` — dynamic ALTER TABLE for unseen cols.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "EntityMap addRow getRow mapping sqlite", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt SQL-backed scratch mapping only when you need ad-hoc keyed lookups across many columns plus streaming replay; otherwise a Map is simpler. Adapt the key-encoding to your collision domain; omit sqlite3 dependency if you don't need getStream. Coverage caveat: no in-repo tests; source-grounded.
