<!-- capsule-v2 -->
# Storage extension attach — how does an external db_type become a working attached database?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the contract a storage extension must fulfill at ATTACH time, with and without full transaction-manager support?

## Alias-resolved lookup; attach+create_transaction_manager pair OR legacy constructor path
**Path/Symbol:** `src/main/database.cpp:DatabaseInstance::CreateAttachedDatabase` (:197-224); `StorageExtension::Find` after `ExtensionHelper::ApplyExtensionAlias` (:204-205); open-file fallback callback registered in Configure :550.
**Signature:** `shared_ptr<AttachedDatabase> CreateAttachedDatabase(ClientContext&, AttachInfo&, AttachOptions&)`; full-extension branch requires BOTH `storage_extension->attach != nullptr` AND `create_transaction_manager != nullptr`.
**Data Shape:** empty `options.db_type` defaults to the built-in duckdb file format; unknown type → `BinderException("Unrecognized storage type \"%s\"")`.

### Decisive source
```cpp
if (!options.db_type.empty()) {
    auto extension_name = ExtensionHelper::ApplyExtensionAlias(options.db_type);
    auto storage_extension = StorageExtension::Find(config, extension_name);
    if (!storage_extension) throw BinderException("Unrecognized storage type \"%s\"", options.db_type);
    if (storage_extension->attach != nullptr && storage_extension->create_transaction_manager != nullptr) {
        // Use the storage extension to create the initial database.
        return make_shared_ptr<AttachedDatabase>(*this, catalog, *storage_extension, context, info.name, info, options);
    }
    // legacy: extension supplies only the catalog/storage glue
    return make_shared_ptr<AttachedDatabase>(*this, catalog, info.name, info.path, options);
}
// An empty db_type defaults to a duckdb database file.
return make_shared_ptr<AttachedDatabase>(*this, catalog, info.name, info.path, options);
```

**Flow:** ATTACH (or startup path resolution via `DBPathAndType::ResolveDatabaseType`, which may `LoadExternalExtension` for magic-byte-detected files :342-355) → alias normalize → find extension → pick modern vs legacy construction → otherwise default duckdb attach inside one explicit transaction (`CreateMainDatabase` :226-237 sets `is_main_database=true`).
**Invariant:** the two-function capability check decides the AttachedDatabase ctor — passing a half-capable extension must fall back, not crash; main-database creation runs through BeginTransaction/Commit like any user ATTACH.
**Probe:** `grep -n 'storage_extension->attach != nullptr' src/main/database.cpp` → :210; `grep -c 'make_shared_ptr<AttachedDatabase>' src/main/database.cpp` → `3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "CreateAttachedDatabase StorageExtension Find ApplyExtensionAlias AttachOptions db_type", limit: 10 });
```

## Verdict
Adopt capability-probed extension attach with a safe built-in default; adapt your plugin ABI; omit magic-byte detection if you only accept explicit types.
