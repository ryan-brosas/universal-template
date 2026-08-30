<!-- capsule-v2 -->
# Neptune dual-store composition — how do you add a managed secondary text-search store beside a graph backend that has no fulltext/vector indexes?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`graphiti_core/driver/neptune_driver.py`); Codebase Memory `graphiti`. **Question:** When the graph engine (Neptune) cannot host fulltext or vector indexes, how does the driver attach OpenSearch/AOSS as a second store without leaking it into the shared `GraphDriver` interface?

## Composition root + module-global index catalog
**Path/Symbol:** `graphiti_core/driver/neptune_driver.py:NeptuneDriver.__init__` (:142–195), `aoss_indices` (:62–136), `run_aoss_query` (:342–349), `save_to_aoss` (:351–364), `build_indices_and_constraints` (:336–340).
**Signature:** `__init__(self, host: str, aoss_host: str, port: int = 8182, aoss_port: int = 443)`; `run_aoss_query(self, name: str, query_text: str, limit: int = 10) -> dict`; `save_to_aoss(self, name: str, data: list[dict]) -> int`.
**Data Shape:** `host` must carry a scheme — `neptune-db://<endpoint>` selects `NeptuneGraph`, `neptune-graph://<graphId>` selects `NeptuneAnalyticsGraph`; anything else raises `ValueError`. Four index templates (`node_name_and_summary`, `community_name`, `episode_content`, `edge_name_and_fact`), each `{index_name, body(mappings+properties), query(multi_match fields + size)}`, live as a mutable module-global list.

### Decisive source
```python
if host.startswith('neptune-db://'):
    endpoint = host.replace('neptune-db://', '')
    self.client = NeptuneGraph(endpoint, port)
elif host.startswith('neptune-graph://'):
    graphId = host.replace('neptune-graph://', '')
    self.client = NeptuneAnalyticsGraph(graphId)
else:
    raise ValueError('You must provide an endpoint to create a NeptuneDriver as either neptune-db://<endpoint> or neptune-graph://<graphid>')
...
self.aoss_client = OpenSearch(
    hosts=[{'host': aoss_host, 'port': aoss_port}],
    http_auth=Urllib3AWSV4SignerAuth(session.get_credentials(), session.region_name, 'aoss'),
    use_ssl=True, verify_certs=True,
    connection_class=Urllib3HttpConnection, pool_maxsize=20,
)

async def build_indices_and_constraints(self, delete_existing: bool = False):
    # Neptune uses OpenSearch (AOSS) for indexing
    if delete_existing:
        await self.delete_aoss_indices()
    await self.create_aoss_indices()
```

**Flow:** ctor validates scheme → builds graph client → builds SigV4-signed AOSS client (`service='aoss'`, pool 20) → instantiates all eleven ops classes, passing `driver=self` ONLY to `community_node_ops`, `search_ops`, `graph_ops` (the three that need the AOSS bridge); the other eight are stateless no-arg. `build_indices_and_constraints` remaps the ABC's index method onto AOSS: optional delete, then create-each-if-missing followed by **`await asyncio.sleep(60)`** — AOSS index creation completes asynchronously server-side, so searching immediately after create fails; the wait is part of the contract. `save_to_aoss` name-matches a template, projects each doc down to `_index`/`_id`(=uuid)/mapped-properties only, ships via `helpers.bulk(..., stats_only=True)` and returns the success count (or `0` on unmatched name). `run_aoss_query` injects `query_text` into the template's multi_match and returns the raw OpenSearch response (`{}` on unmatched name).
**Invariant:** the AOSS plane is reachable only through `NeptuneDriver.run_aoss_query/save_to_aoss` plus the three driver-back-referenced ops classes; every other driver declares `aoss_client: None = None` (neo4j_driver.py:100, falkordb_driver.py:131, kuzu_driver.py:139) and cross-driver call sites silence the attribute check with `# pyright: ignore reportAttributeAccessIssue`. Never widen `GraphDriver` with AOSS methods.
**Probe:** `tests/utils/search/test_edge_bfs_query_shape.py` (`RecordingNeptuneDriver` drives `NeptuneSearchOperations` against recorded queries — the consumer side of this composition). Coverage caveat: no live AOSS integration test; `tests/helpers_test.py:60` explicitly disables Neptune ("Disable Neptune for now"), so no e2e driver probe exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "NeptuneDriver run_aoss_query save_to_aoss", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the URI-scheme constructor branching, the driver-back-reference pattern for exactly the ops that need the sidecar store, and the sleep-after-create readiness contract. Adapt the SigV4/AOSS specifics to your managed search provider. Omit the module-global mutable template list as-is — see `neptune-aoss-quirks.md` before copying it. Caveat: composition verified against source only; no live-service test exists upstream.
