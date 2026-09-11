<!-- capsule-v2 -->
# Wrapper-agnostic SQLite marshalling — how do you get Grist's column-dictionary Buffer out of ANY SQLite driver, including ones with no custom aggregation support?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you define the minimal SQLite-wrapper contract and a portable `allMarshal` replacement when the driver can't register custom functions?

## `MinDB` capability contract + `grist_marshal` emulated via prepare/columns + UNION-wrapped aggregate
**Path/Symbol:** `app/server/lib/SqliteCommon.ts:MinDB` (:24–60), `MinDBOptions` (:15–22), `gristMarshal` (:100–126), `allMarshalQuery` (:149–156), `_fixParameters` (:163–165).
**Signature:** `interface MinDB { exec(sql): Promise<void>; run/get/all/prepare/runAndGetId/allMarshal(sql, ...params); close(); limitAttach(maxAttach): Promise<void>; interrupt?(): Promise<void>; getOptions?(): MinDBOptions; backup?(filename): Backup }`; `async allMarshalQuery(db: MinDB, sql: string, ...params): Promise<Buffer>`.
**Data Shape:** `MinDBOptions { canInterrupt: boolean; bindableMethodsProcessOneStatement: boolean }` — declared wrapper facts other layers branch on; `ResultRow = {[column]: any}`; `Backup { remaining, failed, step(pages, cb?), finish(cb?) }`.

### Decisive source
```ts
export const gristMarshal = {
  initialize(): GristMarshalIntermediateValue { return {}; },
  step(accum: GristMarshalIntermediateValue, ...row: any[]) {
    if (!accum.names || !accum.values) {
      accum.names = row.map(value => String(value));   // first row supplies column names
      accum.values = row.map(() => []);
    } else {
      for (const [i, v] of row.entries()) { accum.values[i].push(v); }
    }
    return accum;
  },
  finalize(accum) {
    const marshaller = new Marshaller({ version: 2, keysAreBuffers: true });
    ... marshaller.marshal(result); return marshaller.dumpAsBuffer();
  },
};

export async function allMarshalQuery(db: MinDB, sql: string, ...params: any[]): Promise<Buffer> {
  const statement = await db.prepare(sql);
  const columns = statement.columns();                  // need names BEFORE running the query
  const quotedColumnList = columns.map(quoteIdent).join(",");
  const query = await db.all(`select grist_marshal(${quotedColumnList}) as buf FROM ` +
    `(select ${quotedColumnList} UNION ALL select * from (` + sql + "))", ..._fixParameters(params));
  return query[0].buf;
}
```

**Flow:** drivers implement `MinDB`; only `exec` may span multiple semicolon-separated statements, everything else processes exactly one (sqlite3_prepare_v2 semantics, tail ignored). When the driver lacks Grist's forked-in marshalling, `allMarshalQuery` prepares the user SQL solely to read its column list, then wraps it in `SELECT grist_marshal(cols) FROM (SELECT cols UNION ALL SELECT * FROM (<sql>))`: the first UNION branch feeds column NAMES as the aggregate's first row, so `step` can build `{names, values}` before real rows arrive, and `finalize` emits the versioned marshalled Buffer.
**Invariant:** The emulation REQUIRES a custom aggregation registered as `grist_marshal` on the connection plus this exact two-phase step contract (row 0 = names). Booleans must be pre-cast to 1/0 (`_fixParameters`) because node-sqlite3 does it automatically but other wrappers don't. `limitAttach` exists to cap ATTACH-ed databases (sandbox escape surface). The doubled-column projection is deliberate ("hacky UNION… compatibility with the existing marshalling method") — porters who drop the name-row branch get buffers keyed by ordinal instead of colId.
**Probe:** No dedicated unit test file (coverage caveat — consumed via DocStorage's `allMarshal` path, which DocStorageQuery.ts stubs at :27 and asserts through exact-SQL cases :49/:96). Deterministic source probes: `grep -c "UNION ALL" app/server/lib/SqliteCommon.ts` = 1 (:154); `grep -n "keysAreBuffers: true" app/server/lib/SqliteCommon.ts` hits :116 exactly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "allMarshalQuery gristMarshal MinDB SqliteVariant", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when you must swap SQLite drivers (node-sqlite3 ↔ better-sqlite3 ↔ WASM) behind one interface while preserving a binary column-dictionary wire format: declare per-wrapper facts explicitly instead of feature-sniffing at runtime. Adapt the aggregate emulation if your driver supports custom functions natively (then just call it), and your marshaller versioning to your wire format. Omit `interrupt`/`backup` optionality only if your host never cancels queries or snapshots live DBs.
