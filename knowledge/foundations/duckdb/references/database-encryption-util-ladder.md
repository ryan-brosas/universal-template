<!-- capsule-v2 -->
# EncryptionUtil fallback ladder — how do you resolve a crypto provider when httpfs may or may not be loaded?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the decision ladder between mbedtls and OpenSSL-backed httpfs, and what fails loudly?

## force flag → try autoload (install only if writable) → read-only fallback to mbedtls → loud error
**Path/Symbol:** `src/main/database.cpp:DatabaseInstance::GetEncryptionUtil` (:610-646) + `GetMbedTLSUtil` (:600-608).
**Signature:** `shared_ptr<EncryptionUtil> GetEncryptionUtil(bool read_only)`; mbedtls escape hatch = setting `force_mbedtls_unsafe`.
**Data Shape:** returns a shared factory; `config.encryption_util` may already be populated as a side effect of loading httpfs.

### Decisive source
```cpp
if (force_mbedtls) return GetMbedTLSUtil(force_mbedtls);       // explicit unsafe override
if (!config.encryption_util) {
    if (read_only) TryAutoLoadAvailableExtension(*this, "httpfs");  // load, never install
    else           TryAutoLoadExtension(*this, "httpfs");          // install+load allowed
}
if (config.encryption_util) return config.encryption_util;      // provided via httpfs
if (read_only) return GetMbedTLSUtil(force_mbedtls);            // read-only: mbedtls suffices
throw InvalidConfigurationException(" DuckDB currently has a read-only crypto module loaded. ... "
    "To write an encrypted database or parquet file that is NOT securely encrypted, one can use "
    "SET force_mbedtls_unsafe = 'true'.");
```

**Flow:** honor the forced-mbedtls flag → otherwise attempt to obtain the stronger httpfs-provided util (install permitted only for writable databases) → read-only databases settle for mbedtls → writes with neither provider throw an InvalidConfigurationException that names the exact remediation.
**Invariant:** read_only never triggers an INSTALL side effect; the error message must offer the unsafe opt-in because silently downgrading write encryption is not acceptable.
**Probe:** `grep -n 'TryAutoLoadAvailableExtension(\*this, "httpfs")' src/main/database.cpp` → :622; `grep -c 'GetEncryptionUtil' src/main/database.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "GetEncryptionUtil GetMbedTLSUtil TryAutoLoadAvailableExtension httpfs force_mbedtls", limit: 10 });
```

## Verdict
Adopt capability-then-fallback resolution where read-only paths avoid side effects; adapt extension names; omit mbedtls specifics if your platform ships one canonical crypto backend.
