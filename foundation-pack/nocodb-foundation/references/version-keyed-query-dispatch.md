<!-- capsule-v2 -->
|# version-keyed query dispatch — how do dialect clients pick SQL per server version, and why does mysql's `[rows, fields]` shape leak into every list method?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the _getQuery contract, and what response-shape conventions must a porter reproduce?

## version-keyed query dispatch
**Path/Symbol:** `MysqlClient._getQuery` (:1867–1887), `version` (:230–259), `columnList` MariaDB NULL coercion (:680–691, issue #4625), `getDataTypes` (:270–290); pg twin `PgClient._getQuery` (:1949–1970) + `dateConversionFunction` consumer :3288; sqlite twin :1054–1075. Query catalogs: `mysql.queries.ts` (26 `default:` blocks; `'55'`/`'56'` legacy keys), `pg.queries.ts`, `sqlite.queries.ts`.
**Signature:** `_getQuery({func}): string` — resolves `queries[func][this._version.key]?.sql ?? queries[func].default.sql`; `_version` lazily populated by one `version()` round-trip.
**Data Shape:** version key = `primary+major` STRING CONCATENATION (`'8' + '0'` → `'80'`, `'5' + '7'` → `'57'`) — NOT arithmetic.

### Decisive source
```ts
// _getQuery — identical in all three clients:
if (isEmpty(this._version)) { const result = await this.version(); this._version = result.data.object; }
if (this._version.key in this.queries[args.func]) return this.queries[args.func][this._version.key].sql;
return this.queries[args.func].default.sql;

// MysqlClient.version — the [rows, fields] tuple convention:
const data = await this.sqlClient.raw('select version() as version');
result.data.object.version = data[0][0].version;   // data[0]=rows array, data[1]=fields
if (versions.length === 3) { primary=versions[0]; major=versions[1]; minor=versions[2];
  key = versions[0] + versions[1]; }               // STRING concat: "5"+"7"→"57"
else result.code = -1;                             // MariaDB multi-part versions REJECTED here
```
MariaDB default-string coercion (#4625, verbatim comment :680–684): MySQL keeps NULL unquoted while MariaDB wraps a provided string NULL in quotes, so `if (this._version.version.includes('Maria')) if (column.cdf === 'NULL') column.cdf = null;`. Every SHOW-style list method guards with `if (response.length === 2)` before touching `response[0]` — the knex-mysql two-element shape IS the API.

**Flow:** first introspection call → version() pins {version,primary,major,minor,key} on the instance → every catalog query asks _getQuery for the dialect×version SQL text → raw(sql, params) → normalize rows (`mapKeys(...,k=>k.toLowerCase())` because MySQL returns UPPERCASE keys from information_schema) → map into the cross-dialect column/index/relation vocabulary ({tn,cn,dt,np,ns,clen,cop,pk,nrqd,un,ai,unique,cdf}).

**Invariant:** (1) Version keys are string concatenations — computing them numerically ('8'+'0'=80 as number) misses every catalog entry. (2) The lazy `_version` latch is per-client-instance: a client constructed BEFORE a version upgrade keeps stale SQL until recreated; porters caching clients across migrations inherit this. (3) `response.length === 2` is a SHAPE assertion, not an error check — treating falsy rows as empty lists instead of wrong-shape hides driver breakage. (4) Lowercasing happens AFTER fetch, BEFORE field access, everywhere; skipping it makes code work on one driver and crash on another. (5) MariaDB detection rides the SAME version string that failed the 3-part parse — the coercion lives in columnList precisely because version() rejects Maria's 4-part versions into result.code=-1 while still setting `.version`.

**Probe:** runner BLOCKED (no upstream spec imports MysqlClient) → deterministic probes at pin: `grep -n "includes('Maria')" packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` resolves :686 single site; `grep -c "response.length === 2" packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` ≥ 15; `sed -n '244,246p' packages/nocodb/src/db/sql-client/lib/mysql/MysqlClient.ts` shows `key = versions[0] + versions[1];` concat verbatim.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "_getQuery version key MysqlClient queries", limit: 10 });
```

## Verdict
Adopt lazy version latching + `{func: {default|<key>: {sql}}}` catalogs and the lowercase-on-fetch normalization; adapt version detection to host drivers but keep the string-concat key rule; omit the `[rows, fields]` guard only if your driver returns row arrays directly.
