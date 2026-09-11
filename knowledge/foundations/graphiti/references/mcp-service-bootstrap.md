<!-- capsule-v2 -->
# MCP service bootstrap — degraded-LLM/embedder, fatal-reranker, provider-branched errors

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** in a server that builds its memory stack from config at boot, which component failures degrade to warnings and which must abort startup — and how are connection failures translated for operators?

## MCP service bootstrap (composition + failure policy)
**Path/Symbol:** `mcp_server/src/graphiti_mcp_server.py`: `GraphitiService` (:190-351), `initialize` (:202-343) — factory try/except pairs (:209-224), FalkorDB-vs-Neo4j construction branch (:237-267), connection-error translation ladder (:268-306), lazy `get_client` (:345-351).
**Signature:** `async initialize(self) -> None`; `semaphore_limit: int = 10` shared by `asyncio.Semaphore` and `max_coroutines`.
**Data Shape:** `self.entity_types/edge_types/edge_type_map` built from config BEFORE client init; driver chosen by `config.database.provider.lower()`.

### Decisive source
```python
# DEGRADED: LLM and embedder creation failures only warn — the server still
# boots with reduced capability (search-only / limited extraction):
try:
    llm_client = LLMClientFactory.create(self.config.llm)
except Exception as e:
    logger.warning(f'Failed to create LLM client: {e}')
...
# FATAL: cross-encoder is created OUTSIDE any try/except on purpose.
# Without it Graphiti silently defaults to OpenAIRerankerClient, which needs
# an OpenAI key even on non-OpenAI stacks:
cross_encoder_client = CrossEncoderFactory.create(self.config.llm, self.config.embedder)

# CONNECTION failures get operator-actionable, provider-specific RuntimeErrors;
# everything else re-raises unchanged:
error_msg = str(db_error).lower()
if 'connection refused' in error_msg or 'could not connect' in error_msg:
    if db_provider.lower() == 'falkordb':
        raise RuntimeError(f'...FalkorDB is not running...\n  docker run -p 6379:6379 falkordb/falkordb\n...')
    ...
    raise RuntimeError(...) from db_error
# Re-raise other errors
raise
```

**Flow:** build typed models from YAML config → create LLM + embedder through factories (each failure warns, leaves None) → create cross-encoder (failure propagates) → build driver config → branch: `falkordb` constructs `FalkorDriver(host, port, username, password, database)` directly; otherwise classic `Graphiti(uri, user, password)` Neo4j path → translate connection-refused into per-provider runbook errors → `build_indices_and_constraints()` → log effective providers/group_id. `get_client()` lazily initializes once and raises `RuntimeError('Failed to initialize Graphiti client')` if still None.
**Invariant:** (1) the degraded/fatal split is a POLICY, not an accident — reranker failure must stay fatal because the silent default would mis-rank results behind a misleading success; (2) substring matching on lowercased exception text (`connection refused`, `could not connect`) is the ONLY thing distinguishing "backend down" from "bad config" — other exceptions must pass through untouched; (3) one semaphore limit feeds both asyncio concurrency and `Graphiti.max_coroutines` so tool calls and internal gathers share one budget.
**Probe:** anchored at repo root. Battery: `grep -c 'reasoning_prefixes' graphiti_core/llm_client/azure_openai_client.py` → 2 (Azure reasoning-model gate consumed by this bootstrap's clients); `grep -n "if self.config.database.provider.lower() == 'falkordb'" mcp_server/src/graphiti_mcp_server.py` → line 238; `grep -n "cross_encoder_client = CrossEncoderFactory.create" mcp_server/src/graphiti_mcp_server.py` → line 224 (outside try/except). Direct-test caveat: mcp_server unit suite (`tests/test_core_parity.py`) requires `pydantic_settings`, absent from the core `.venv` — suite uncollectable here; recorded as env-gated BLOCKED-RUNNER, contract verified against source.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "GraphitiService initialize CrossEncoderFactory FalkorDriver build_indices_and_constraints", limit: 6, fields: ["signature", "name", "file"] });
// rank-1 line-exact: mcp_server .../graphiti_mcp_server.py :202-343
```

## Verdict
Adopt the explicit degrade-vs-fail component policy and operator-runbook error translation for any service assembling provider clients from config; adapt provider branches and substrings to your backends; omit the FalkorDB direct-construction branch when your host always goes through URI-based drivers. Coverage caveat stated above.
