<!-- capsule-v2 -->
|# ncMeta.now() — the client-aware timestamp every meta-database time comparison must use

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Why do backfill jobs snapshot time with `ncMeta.now()` instead of `new Date()` — and what breaks if a porter "simplifies" it?

## Path/Symbol
`packages/nocodb/src/meta/meta.service.ts:now` (1096–1100); consumer exemplar `modules/jobs/migration-jobs/nc_job_015_pg_source_searchpath_backfill.ts:94`.

**Signature:** `now(): string` — `dayjs().utc().format(isMySQL() ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD HH:mm:ssZ')`.

**Data Shape:** a STRING in exactly the format nc_meta columns store: MySQL gets no zone suffix (driver/session tz handles it); pg/sqlite/mssql get an explicit Z offset.

### Decisive source
```ts
public now(): any {
  return dayjs()
    .utc()
    .format(this.isMySQL() ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD HH:mm:ssZ');
}
// nc_job_015 call-site comment:
// Use ncMeta.now() (client-aware), NOT new Date(): created_at is stored as a
// string in ncMeta.now()'s format, and on a SQLite meta DB a bound Date binds
// as a numeric (node-sqlite3), so `TEXT < numeric` is ALWAYS false (SQLite
// storage-class ordering) — the job would find 0 candidates and grandfather
// nothing. MySQL has an analogous timezone-offset bug. Only PG tolerates a raw Date.
```

**Flow:** any job filtering meta rows by time (`created_at < X`) builds X with this method so the bound value's TYPE and FORMAT match stored strings across all three meta dialects.

**Invariant:** (1) Meta timestamps are STRINGS compared format-exact — never bind JS Dates against them. (2) SQLite storage classes make cross-type comparisons silently FALSE (no error, zero rows): failure mode is a no-op migration, worse than a crash. (3) UTC applied before formatting so offsets can't drift between app servers sharing a meta DB.

**Probe:** no unit test upstream. Source-grounded probe: meta.service.ts:1096-1100 whole method, nc_job_015:88-93 comment verbatim, pairing capsule migration-searchpath-grandfather.md (startedAt usage).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "metaService now dayjs utc format isMySQL", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt client-aware string timestamp generation for ALL meta-table time comparisons; adapt format tokens per host; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
