<!-- capsule-v2 -->
# SQLite adapter hardening — what must a node SQLite driver wrapper declare and forbid before Grist will trust it?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does a thin driver adapter make a quirky callback-based sqlite library safe for serialized multi-tenant document storage?

## NodeSqlite3DatabaseAdapter
**Path/Symbol:** `app/server/lib/SqliteNode.ts:NodeSqlite3DatabaseAdapter` (33-133), `limitAttach` (113-132), `opener` (34-43), `getOptions` (96-101).
**Signature:** `static opener(dbPath: string, mode: OpenMode): Promise<MinDB>`; `limitAttach(maxAttach: number): Promise<void>`; `getOptions(): MinDBOptions`; implements the `MinDB` contract from SqliteCommon.
**Data Shape:** Wraps `@gristlabs/sqlite3` (fork with built-in Grist marshalling + `allMarshal`). Capability declaration: `{ canInterrupt: true, bindableMethodsProcessOneStatement: true }`.

### Decisive source
```ts
public constructor(protected _db: sqlite3.Database) {
  // Default database to serialized execution. This isn't enough for
  // transactions, which we serialize explicitly.
  this._db.serialize();
}
public static async opener(dbPath, mode) {
  ...
  await result.limitAttach(0);  // Outside of VACUUM, we don't allow ATTACH.
  return result;
}
public async limitAttach(maxAttach: number) {
  const SQLITE_LIMIT_ATTACHED = (sqlite3 as any).LIMIT_ATTACHED;
  // Work around node-sqlite3 bug when .configure() is called while a query is running
  await new Promise<void>((resolve) => {
    (this._db as any).wait(() => {
      // pending==0 guaranteed here; Configure() applies the new limit immediately
      (this._db as any).configure("limit", SQLITE_LIMIT_ATTACHED, maxAttach);
      resolve();
    });
  });
}
```

**Flow:** Open maps `OpenMode` → lib flags bit-wise, then IMMEDIATELY denies `ATTACH` (`limitAttach(0)`) so documents cannot reach outside their file. Constructor calls `serialize()` — the lib's own queue orders statements but is explicitly NOT sufficient for transactions (upper layers chain promises/execTransaction themselves). Any future `configure()` must run inside `wait(...)` because configuring mid-query trips upstream bug TryGhost/node-sqlite3#1838 (documented with source links at 118-131). `prepare` resolves via a captured-variable dance (`.then(() => stmt)`, throwing if unset); the prepared statement's `columns()` deliberately THROWS since the fork has marshalling built in (only non-fork wrappers need `columns()` for the UNION-trick marshal emulation in sqlite-minimal-wrapper-contract). `allMarshal`/`lastID` exist only on the fork (casts bypass stale typings).
**Invariant:** The `MinDBOptions` capability facts must tell the truth — `runSQLQuery`'s refusal ladder keys on them, and a wrapper lying about `bindableMethodsProcessOneStatement` reintroduces multi-statement injection. ATTACH stays denied by default; serialize() never substitutes for explicit transaction serialization.
**Probe:** No dedicated unit file for SqliteNode (coverage caveat); the adapter runs under `test/server/lib/DocStorage.js` and the wider DocStorage suites. Deterministic anchors: `grep -n "limitAttach(0)\|serialize()" app/server/lib/SqliteNode.ts` → :41/:48.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "NodeSqlite3DatabaseAdapter limitAttach", limit: 5 });
```
## Verdict
Adopt deny-by-default ATTACH, wait-guarded runtime configuration, honest capability declarations, and serialize-but-still-explicitly-transaction discipline for any driver adapter; adapt flag names to your library; omit the fork-specific allMarshal plumbing if your driver lacks built-in marshalling (then pair with the minimal-wrapper-contract capsule instead).
