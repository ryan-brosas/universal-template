<!-- capsule-v2 -->
|# Driver coercion funnel — tedious's strict typing normalized at exactly one chokepoint

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Where do you normalize driver-hostile option types when persisted form data is strings — per call site, or at one funnel?

## Path/Symbol
`packages/nocodb/src/models/Source.ts:normalizeMssqlConfig` (356–417); invoked from getConfig on ALL three return paths (:434, :438, :474).

**Signature:** `protected normalizeMssqlConfig(config): any` — no-op unless `config.client === 'mssql'`.

**Data Shape:** numeric keys: port/connectTimeout/requestTimeout. Boolean keys: encrypt/trustServerCertificate/enableArithAbort/readOnlyIntent/abortTransactionOnError ('true'/'false' strings → booleans; 'strict' left for tedious to judge). TDS packetSize default 16384 only when neither nesting level sets one.

### Decisive source
```ts
// MSSQL's tedious driver strictly requires typed connection options:
//   port — must be a number ... encrypt — strict boolean check
//   (typeof === 'boolean'); string "true" silently treated as falsy ...
//   trustServerCertificate — strict boolean; tedious THROWS TypeError
// getConfig() is the one method every connection path funnels through —
// CE + EE getConnectionConfig and getSourceConfig all call it — so
// normalize here, guarded to mssql only.
conn.options = conn.options ?? {};
if (conn.options.packetSize == null && conn.packetSize == null) {
  conn.options.packetSize = 16384;
}
```

**Flow:** every getConfig exit passes the guard → non-mssql returns untouched → mssql gets numeric/boolean coercion at BOTH `connection` and `connection.options` levels → packet-size default applied without overriding explicit values.

**Invariant:** (1) Coercion must live where EVERY path already converges; sprinkling Number()/==='true' at call sites guarantees CE/EE drift. (2) Coerce conservatively: only exact 'true'/'false' flip — other strings pass so the DRIVER raises the real validation error (e.g. encrypt='strict' is valid). (3) Defaults never override explicit values (`== null` across both levels). (4) Client guard keeps O(1) cost for everyone else.

**Probe:** no unit test upstream. Source-grounded probe: Source.ts:356-366 comment verbatim, :372-405 coerce loops, :407-414 packet-size rationale ("large result sets fragment into many small packets").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "normalizeMssqlConfig tedious packetSize trustServerCertificate", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt single-funnel driver coercion with conservative flipping and default-without-override; adapt key lists per driver; omit non-mssql drivers. Coverage caveat: no in-repo unit tests; source-grounded.
