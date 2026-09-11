<!-- capsule-v2 -->
# DatabaseInstance Initialize — what is the exact construction order, and why do threads start last?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** In what order must a DB instance assemble managers/pool/catalog, and where does extension-setting replay fit?

## Configure → filesystems → buffer manager → scheduler → catalog → main attach → threads
**Path/Symbol:** `src/main/database.cpp:DatabaseInstance::Initialize` (:297-367); `Configure` (:479-568); destructor teardown :90-114.
**Signature:** `void Initialize(const char *database_path, DBConfig *user_config)`; thread start deliberately deferred: "only increase thread count after storage init because we get races on catalog otherwise" (:363).
**Data Shape:** config defaults resolved in Configure: access_mode READ_WRITE when undefined; temp dir defaulted; `maximum_memory`/`maximum_threads`/`async_threads` filled from system when INVALID_INDEX.

### Decisive source
```cpp
Configure(*config_ptr, database_path);
ExtensionHelper::RegisterLinkedExtensions(config);
create_api_v1 = CreateAPIv1Wrapper;
db_file_system = make_uniq<DatabaseFileSystem>(*this);
...
buffer_manager = make_uniq<StandardBufferManager>(*this, config.options.temporary_directory);
...
scheduler = make_uniq<TaskScheduler>(*this);          // created BEFORE threads launch
object_cache = make_uniq<ObjectCache>(*config.buffer_pool);
config.buffer_pool->SetObjectCache(object_cache.get());
...
LoadExtensionSettings();                              // autoload + unrecognized-option replay
if (!db_manager->HasAttachedDatabase()) CreateMainDatabase();
// only increase thread count after storage init because we get races on catalog otherwise
scheduler->SetThreads(config.options.maximum_threads, Settings::Get<ExternalThreadsSetting>(config));
scheduler->SetAsyncThreads(config.options.async_threads);
scheduler->RelaunchThreads();                          // LAST step
```

**Flow:** configure → publish linked extensions → build fs/db-manager/buffer-manager/log/metrics/cache/result-set/scheduler/object-cache/connection/extension managers → init secrets → resolve/open db type (load storage extension if foreign) → replay extension settings inside one transaction → attach main database → size and relaunch worker threads.
**Invariant:** nothing may enqueue work before `RelaunchThreads()`; the destructor mirrors the order in reverse — connections first, log manager LAST-before-buffer ("after this point Logger calls are unsafe"), allocator flush + background-thread disable at the end.
**Probe:** `grep -n 'only increase thread count after storage init' src/main/database.cpp` → :363 comment; `grep -n 'scheduler->SetThreads\|scheduler->RelaunchThreads' src/main/database.cpp` → :364/:366.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "DatabaseInstance Initialize Configure CreateMainDatabase RelaunchThreads LoadExtensionSettings", limit: 10 });
```

## Verdict
Adopt the ordering contract (managers → catalog data → settings replay → attach → threads) and its mirrored teardown; adapt manager granularity; omit C-API v1 wiring if you expose no C surface.
