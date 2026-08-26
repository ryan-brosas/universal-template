<!-- capsule-v2 -->
# MCP tool ingestion — how do external MCP servers become smolagents Tools, and what does the context manager own?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What are the transport rules for `ToolCollection.from_mcp`/`MCPClient`, when does the connection actually open, and what changes with `structured_output=True`?

## Adapt-through-MCPAdapt with eager connect
**Path/Symbol:** `src/smolagents/tools.py:ToolCollection.from_mcp` (:949-1058); `src/smolagents/mcp_client.py:MCPClient` (:33-171, connect in __init__ :122, get_tools guard :150-154).
**Signature:** `from_mcp(server_parameters: StdioServerParameters | dict, trust_remote_code=False, structured_output=None) -> ContextManager[ToolCollection]`; dict form REQUIRES "url" and optional transport ∈ {streamable-http (default), sse}.
**Data Shape:** Yields the ToolCollection whose `.tools` are plain smolagents Tool objects adapted by mcpadapt's SmolAgentsAdapter; `structured_output` toggles outputSchema/structuredContent/JSON-fallback support.

### Decisive source
```python
# tools.py :1052-1057 — trust gate + adapter construction:
if not trust_remote_code:
    raise ValueError("Loading tools from MCP requires you to acknowledge you trust the MCP server, ...")
with MCPAdapt(server_parameters, SmolAgentsAdapter(structured_output=structured_output)) as tools:
    yield cls(tools)
# mcp_client.py :156-162 — ALREADY connected at __enter__ because init connected:
def __enter__(self) -> list[Tool]:
    return self._tools
```

**Flow:** Both entry points funnel into MCPAdapt; a background thread runs the asyncio loop for the server session. `MCPClient.__init__` calls `self.connect()` immediately — constructing without a `with` block leaks an open session unless you call disconnect() in finally (docstring-mandated). `get_tools()` returns session-start inventory only (documented limitation) and raises ValueError if accessed pre-connect. Transport defaulting mutates the caller's dict in place to record the chosen "streamable-http". The structured_output flag is mid-migration: unspecified → FutureWarning + False until v1.25 flips default True.
**Invariant:** Trust gate is mandatory on BOTH paths because MCP tools execute locally after adaptation. The context-manager contract differs subtly between the two classes: `with MCPClient(...)` yields the TOOL LIST (`__enter__ -> list[Tool]`), while `with ToolCollection.from_mcp(...)` yields the collection wrapper — porters who normalize them break every example.
**Probe:** `tests/test_mcp_client.py` (client lifecycle incl. error paths). Live: construct MCPClient against absent server → connection error at __init__ time (eager-connect proof); get_tools() before connect → ValueError.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "ToolCollection from_mcp MCPClient structured_output", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt eager-connect-with-context-manager and the dual yield-type distinction. Adapt transports per your MCP client lib. Omit the FutureWarning migration valve if your API is already past its own flip.
