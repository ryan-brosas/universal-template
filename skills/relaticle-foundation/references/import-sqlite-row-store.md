<!-- capsule-v2 -->
# Per-import SQLite store — ephemeral dataset as a first-class database

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you stage tens of thousands of CSV rows for wizard-style validation/review without bloating the primary database or losing SQL semantics?

## ImportStore dynamic connection + SQLite triggers
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportStore.php` (whole, 201L): `create()` (:24-33), `load()` (:35-50), `createConnection()` (:150-162), `createTableSafely()` (:164-200), `bulkUpdateMatches()` (:101-142), `ensureProcessedColumn()` (:85-96).
**Signature:** `ImportStore::load(string $importId): ?self`; `query(): EloquentBuilder<ImportRow>`; `connectionName(): string // "import_{id}"`
**Data Shape:** One directory per import: `storage_path("app/imports/{id}")/data.sqlite`. Table `import_rows`: `row_number` PK, `raw_data` TEXT (JSON), nullable JSON columns `validation`/`corrections`/`skipped`, `match_action`, `matched_id`, `relationships`, `processed`.

### Decisive source
```php
private function createTableSafely(): void {
    ...
    $this->connection()->statement('
        CREATE TRIGGER validate_raw_data_insert
        BEFORE INSERT ON import_rows
        BEGIN
            SELECT CASE
                WHEN NEW.raw_data IS NULL OR NEW.raw_data = \'\' OR NEW.raw_data = \'{}\'
                THEN RAISE(ABORT, \'raw_data cannot be null or empty\')
            END;
        END
    ');
    $schema->table('import_rows', function (Blueprint $table): void {
        $table->index('validation'); $table->index('match_action'); $table->index('skipped');
    });
}
```
Connection registration is runtime config injection: `resolve(Repository::class)->set("database.connections.{$name}", $config)` then `ConnectionFactory::make($config, $name)` — no config-file edits.

**Flow:** `create()` = ensure dir → truncate-create file → schema+trigger+indexes; `load()` = ULID-format gate (`Str::isUlid`) + existence check before connecting (path-traversal guard); queries always via `ImportRow::on($connectionName())`; `ensureProcessedColumn()` migrates old stores idempotently; `destroy()` drops connection ref then deletes directory.
**Invariant:** The Eloquent model must never be used without binding to the per-import connection (`ImportStore::query()`, not `ImportRow::query()`); `load()` must refuse non-ULID ids BEFORE touching the filesystem.
**Probe:** `tests/Feature/ImportWizard/Commands/CleanupImportsCommandTest.php` + store usage pinned throughout `tests/Feature/ImportWizard/Jobs/*` (no dedicated store unit suite at this pin — caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ImportStore createConnection createTableSafely bulkUpdateMatches", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "ephemeral dataset = its own SQLite file with runtime-registered connection, integrity trigger, and ULID-gated load" for any staging/wizard workload — it buys real SQL (DISTINCT over json_extract, temp-table joins) for free. Adapt paths and the Laravel-specific Repository/Factory injection to your framework's dynamic-connection mechanism. Omit the concrete column set if your domain differs. Coverage caveat: no isolated upstream test file for ImportStore itself.
