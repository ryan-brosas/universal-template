<!-- capsule-v2 -->
# Persisted-schema storage — how do you snapshot a schema so its hash is stable under reordering?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Where does the sync gate keep its "last synced schema", and what makes its hash a reliable change signal?

## Single-row history, delete-then-insert, tables sorted before hashing
**Path/Symbol:** `packages/core/database/src/schema/storage.ts` : `hashSchema` (67–74), `read` (27–65), `add` (76–92).
**Signature:** `hashSchema(schema: Schema): string` (sha256 hex); `async read(): Promise<{ id, time, hash, schema } | null>`; `async add(schema)`; storage table holds one row at a time.
**Data Shape:** row stores JSON-stringified schema + hash + time; read parses JSON back.

### Decisive source
```ts
hashSchema(schema: Schema) {
  // Sort tables by name for deterministic hashing regardless of insertion order
  const sorted = {
    ...schema,
    tables: schema.tables.toSorted((a, b) => a.name.localeCompare(b.name)),
  };
  return crypto.createHash('sha256').update(JSON.stringify(sorted)).digest('hex');
},

async add(schema: Schema) {
  await checkTableExists();
  // NOTE: we can remove this to add history
  await db.getConnection(TABLE_NAME).delete();
  const time = new Date();
  await db.getConnection().insert({ schema: JSON.stringify(schema), hash: this.hashSchema(schema), time })
    .into(TABLE_NAME);
},

// read(): 'We get the ID first before fetching the exact entry for performance on
// MySQL/MariaDB' — select('id').orderBy('time','DESC').first() then select('*').where({id})
```

**Flow:** every completed `syncSchema` replaces the single persisted row with the now-current schema+hash. Boot compares `hashSchema(metadata→schema)` against the stored hash — equal means the metadata projection is byte-stable since last sync.
**Invariant:** the hash must be computed over a canonical form — table order in metadata is insertion-dependent, so unsorted hashing would trigger spurious full diffs (and real DDL) on every boot. `toSorted` also guarantees the input array is not mutated (test-pinned).
**Probe:** `src/schema/__tests__/storage.test.ts` — 'matches regardless of table order' and 'does not mutate the schema tables array'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "migration storage lock shouldRun execute", limit: 30, fields: ["lines", "signature"] });
// returned schema.storage.read @ storage.ts 27-65, hashSchema @ 67-74, add @ 76-92
```

## Verdict
Adopt canonical-form-before-hash and single-row replace semantics for the schema snapshot. Adapt the two-step MySQL id fetch to your dialect's query cost profile (it exists because of issue #20312). Omit the history comment (`we can remove this to add history`) — Strapi deliberately keeps one row. Coverage: all cited paths `no_recorded_issue`.
