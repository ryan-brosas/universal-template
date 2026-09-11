<!-- capsule-v2 -->
# Chroma client-mode selection — how does one constructor serve embedded, server, and cloud clients with a fixed priority ladder?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what is the client-injection precedence and what defaults are forced for each Chroma deployment mode?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/chroma.py`: `ChromaDB.__init__` (:24-74).
**Signature:** `__init__(collection_name, client=None, host=None, port=None, path=None, api_key=None, tenant=None)`.
**Data Shape:** three mutually-exclusive modes resolved by argument presence: injected client → CloudClient (api_key AND tenant both required) → local/server via Settings; collection created eagerly in __init__ (`get_or_create_collection`).

### Decisive source
```python
if client:
    self.client = client
elif api_key and tenant:
    self.client = chromadb.CloudClient(api_key=api_key, tenant=tenant,
        database="mem0")   # Use fixed database name for cloud
else:
    self.settings = Settings(anonymized_telemetry=False)
    if host and port:
        self.settings.chroma_server_host = host
        self.settings.chroma_server_http_port = port
        self.settings.chroma_api_impl = "chromadb.api.fastapi.FastAPI"
    else:
        if path is None:
            path = "db"
    self.settings.persist_directory = path
    self.settings.is_persistent = True
self.collection = self.create_col(collection_name)
```

**Flow:** precedence client > cloud(api_key+tenant) > http-server(host+port) > embedded persistent dir ("db" default) → telemetry disabled unconditionally in non-cloud modes → get_or_create_collection runs at construction so the store is immediately usable (contrast pgvector's lazy _ensure_collection — chroma has no lazy path).
**Invariant:** the injected-client branch wins over EVERYTHING (test fixtures exploit this: pass a Mock as `client` and no chromadb machinery is touched) and cloud requires BOTH credentials (half-configured cloud args silently fall through to local mode); embedded mode always persists (is_persistent=True) with anonymized telemetry off. A porter who reorders these branches breaks mock-based testing first, then silently strands cloud users on a local "db" directory.
**Probe:** `grep -n 'database="mem0"' mem0/vector_stores/chroma.py` (exactly :54); `grep -n "anonymized_telemetry=False" mem0/vector_stores/chroma.py`.
**Direct test:** `tests/vector_stores/test_chroma.py` fixtures (:9-20) pin the injected-client branch; config acceptance pinned by `test_chroma_config_accepts_default_tmp_path` (:337) / `test_chroma_config_rejects_no_config` (:343).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "ChromaDB __init__ CloudClient Settings persist_directory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung mode ladder (injected > cloud-pair > server-pair > embedded-default) with eager get_or_create; adapt default db/path names to your product; omitting telemetry-off or is_persistent changes operational behavior silently. Direct tests cover the injected branch + config gates (cloud arms exercised only via source/docstring — minor caveat recorded).
