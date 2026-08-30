<!-- capsule-v2 -->
# ImportStore: per-import throwaway SQLite — how does one import get its own relational store without polluting the app database?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** how is a scratch relational workspace created, connected at runtime, and destroyed — safely under multi-tenancy?

## Runtime connection registration keyed by import ULID
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportStore.php` (`createConnection` :150-162, `create` :24-33, `load` :35-50, `connection` :72-75).
**Signature:** `final class ImportStore { __construct(private readonly string $id); static create(string $importId): self; static load(string $importId): ?self; connection(): Connection; query(): EloquentBuilder<ImportRow>; destroy(): void }`
**Data Shape:** storage layout `storage_path("app/imports/{ulid}/data.sqlite")`; connection name `"import_{ulid}"` registered into config `database.connections.{name}` with driver sqlite + `foreign_key_constraints => true`; row table `import_rows(row_number PK, raw_data JSON text, validation, corrections, skipped, match_action, matched_id, relationships, processed)` plus three indexes (validation/match_action/skipped).

### Decisive source
```php
public static function load(string $importId): ?self
{
    if (! Str::isUlid($importId)) {
        return null;                       // path-traversal guard: only ULIDs reach filesystem paths
    }
    ...
}
private function createConnection(): Connection
{
    $name = $this->connectionName();       // "import_{id}"
    $config = ['driver' => 'sqlite', 'database' => $this->sqlitePath(), 'foreign_key_constraints' => true];
    resolve(Repository::class)->set("database.connections.{$name}", $config);
    return resolve(ConnectionFactory::class)->make($config, $name);
}
```

**Flow:** `create()` → mkdir + truncate file + `createTableSafely()` (hasTable guard → create schema → install BEFORE INSERT trigger rejecting null/empty/`{}` raw_data) → return instance. Any later reader uses `load()`, which re-validates the id shape and file existence before memoizing the connection in `$this->connection ??= ...`. `query()` returns `ImportRow::on($connectionName())` so every row operation rides the per-import DB. `destroy()` nulls the memoized connection then deletes the directory.
**Invariant:** the connection name embeds the import id so concurrent imports never share a sqlite handle; `Str::isUlid` on load is the security boundary between user input and `storage_path` interpolation. The raw_data trigger makes an empty-row insert abort inside SQLite, not inside app validation.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:110 "creates new People records", :281 skip rows) exercises rows round-tripped through the store; `tests/Feature/ImportWizard/Livewire/ImportWizardTest.php:135` ("cancelImport destroys store"). NOTE: `transitionToImporting` on the Import model has no direct test at this pin.
**Coverage caveat:** no upstream test pins the trigger or `Str::isUlid` guard directly — verified by source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ImportStore createTableSafely createConnection", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: throwaway per-unit relational stores for heavy row-shaped work (validation, set-based updates) instead of fat session arrays or temp CSVs; runtime connection registration scoped by a validated id. Adapt storage root/config keys to your framework. Omit Laravel-specific container resolves if your DI differs — the contract is "register config, factory-make, memoize".
