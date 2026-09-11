<!-- capsule-v2 -->
|# default-value function allowlist — which zero-arg SQL functions may ride in a column DEFAULT, and why is a generic `\w+()` match an information-disclosure hole?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does sanitiseDefaultValue decide between literal, keyword, and function-call defaults, and what is the failure mode of over-admitting?

## default-value function allowlist
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/KnexClient.ts:allowedDefaultFunctions` (:29–62), `sanitiseDefaultValue` (:1910–1957); sole dialect override: `SqliteClient.genValue` (:2293–2299).
**Signature:** `sanitiseDefaultValue(value: string|number|boolean): string|undefined`; module-scoped `Set<string>` compared case-insensitively after `.trim()`.
**Data Shape:** returns knex-bound quoted literal, bare keyword (NULL/TRUE/FALSE), allowlisted `fn()`, CURRENT_TIMESTAMP family, or throws badRequest.

### Decisive source
```ts
// :22–28 — the rationale lives IN SOURCE:
// Allowlist ... deliberately excludes information-disclosing functions
// (version(), current_user(), current_database(), inet_server_addr(),
// txid_current(), pg_backend_pid(), …). A generic /^\w+\(\)$/ match would let
// any zero-arg function in the server catalog execute during INSERT and surface
// its result through the API.
if (/^\w+\(\)$/.test(value.trim())) {
  if (allowedDefaultFunctions.has(value.trim().toLowerCase())) return value;
  // :1929–1931 — clean 400, not raw 500, so the schema editor gets an actionable error
  NcError.badRequest(`Invalid default value: ${value}`);
}
// :1915 — keywords pass verbatim; :1936–1940 CURRENT_TIMESTAMP[()][ ON UPDATE …] regex;
// :1943–1949 quoted strings unwrapped then genQuery('?', [inner]); else genQuery('?', [value]).
```
Allowlist families (all 25): date/time (`now`, `current_timestamp`, `localtimestamp`, `current_date/time`, mssql `getdate/sysdatetime/sysdatetimeoffset/systimestamp`, oracle `sysdate`, pg precision variants `clock/statement/transaction_timestamp`, `timeofday`, mysql `curdate/curtime/utc_timestamp/utc_date/utc_time/unix_timestamp`); non-disclosing randoms (`rand`, `random`); uuid generators (`uuid`, `uuid_generate_v4`, `gen_random_uuid`, `newid`, `sys_guid`).

**Flow:** schema editor sends cdf string → sanitiseDefaultValue classifies (null/undefined → undefined; keyword; numeric; zero-arg call → ALLOWLIST GATE; CURRENT_TIMESTAMP compound; quoted → unwrap+bind; other string → bind) → emitted into CREATE/ALTER. The SQLite subclass overrides only genValue to let bare `CURRENT_TIMESTAMP` through unquoted (sqlite rejects quoted timestamps as defaults), while inheriting the same allowlist gate.

**Invariant:** (1) The allowlist is deny-by-default across ALL dialects — one shared gate, not per-dialect tables; adding a host function means a code change with review, never user input. (2) Rejection must be badRequest (schema-editor UX contract), not a 500 from the DB rejecting the default later. (3) The gate fires BEFORE quote-unwrapping order matters: a value like `'version()'` (quoted) takes the literal path and stays inert — only BARE calls hit the gate, so stripping quotes first would create the injection this gate exists to stop. (4) Case-insensitive compare but original-case passthrough keeps PG lowercase-fn compatibility without rewriting user input.

**Probe:** runner BLOCKED (no upstream spec imports KnexClient) → deterministic probes at pin: `sed -n '22,31p' packages/nocodb/src/db/sql-client/lib/KnexClient.ts` shows the comment + Set head; `grep -n 'version()' packages/nocodb/src/db/sql-client/lib/KnexClient.ts` hits ONLY inside comments (:25 exclusion list + :1923 rationale — no code path executes version()); `grep -n "CURRENT_TIMESTAMP" packages/nocodb/src/db/sql-client/lib/sqlite/SqliteClient.ts` resolves the single genValue override :2293–2299.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "allowedDefaultFunctions sanitiseDefaultValue KnexClient", limit: 10 });
```

## Verdict
Adopt the deny-by-default allowlist with the four semantic families and the badRequest rejection path; adapt the member set to host-server catalogs (re-audit for information-disclosing functions); omit per-function quoting rules if your ORM binds defaults differently — but keep SOME structural bar between bare-call detection and pass-through.
