<!-- capsule-v2 -->
# Knowledge MCP server — env-resolving token auth, 401-retry client, and the honest error envelope that refuses `partial=True`

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How should a thin MCP server forward to a backend it doesn't own — auth that survives subprocess env mangling and token rotation, and tool errors the LLM can ACT on instead of stack traces?

## 7-tool FastMCP forwarder
**Path/Symbol:** `src/cuga/backend/knowledge/mcp_server.py` (`_resolve_env` :28-45; `_default_backend_url` :48-52; token trio `_get_token`/`_reload_token`/`_read_token_file` :63-89; `_request` :109-123; `_resolve_ingest_file_path` :159-179; `search_knowledge` :199-251; `_identity_headers` :182-188).
**Signature:** tools: `search_knowledge(query, scope="all", agent_id="", thread_id="")`, `ingest_knowledge(file_path, scope, replace_duplicates, ...)`, `ingest_knowledge_url`, `list_knowledge_documents`, `delete_knowledge_document`, `get_ingestion_status`, `get_knowledge_status`.
**Data Shape:** identity rides HTTP headers (`X-Agent-ID` discovered per-call from `/api/agent/context`, `X-Internal-Token`); agent_id is NOT cached so agent switches apply immediately. Errors return `{scope, results: [], error}` — never raised.

### Decisive source
```python
# :36-44 — circular/mangled env detection (MCP subprocess gets KEY=KEY literally)
if val == key:
    return default
if val and "/" not in val and "\\" not in val and val == val.upper() and "_" in val:
    resolved = os.getenv(val)
    if resolved and resolved != val:
        return resolved
    return default

# :223-244 — search errors become data; partial stays False ON PURPOSE
# We do NOT set ``partial=True`` here: with results=[] the call returned
# nothing usable ... Hallucinating from an empty set would be the worst
# possible failure mode. The presence of error alone is the retry signal.
```

**Flow:** every request injects the internal token header → on 401 re-read the token file ONCE (rotation after backend restart) then raise_for_status → lazy client cached until closed (60s/10s-connect timeout, verify=False trust_env=False for localhost) → token file read retries 3× over ~2s because the MCP server starts before the backend writes it → ingest paths resolve through the canonical workspace resolver: absolute paths outside `/workspace` + legacy roots rejected, traversal rejected, missing file → FileNotFoundError — all returned as `{"error": ...}`.
**Invariant:** `partial=True` means "≥1 scope succeeded — answer with what you have"; a failed search returns NOTHING usable so it must ship `error` without `partial` — conflating them invites hallucination-from-empty. Tool docstrings stay TERSE on purpose: scope/query/reading rules live in the system-prompt contract (single source of truth); duplicating them here guarantees drift.
**Probe:** direct tests `tests/unit/test_knowledge_mcp_server.py::test_resolve_ingest_file_path_rejects_host_absolute_path` (:12), `::test_resolve_ingest_file_path_rejects_traversal` (:20), `::test_resolve_ingest_file_path_accepts_workspace_relative_file` (:26), `::test_resolve_ingest_file_path_accepts_virtual_workspace_path` (:38), `::test_resolve_ingest_file_path_rejects_missing_workspace_file` (:53). Coverage caveat: `_resolve_env` ladder, 401-retry, and the no-partial envelope verified by source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "search_knowledge _resolve_env _request _resolve_ingest_file_path X-Internal-Token", limit: 10 });
```

## Verdict
Adopt structured-error tool envelopes with an explicit partial-vs-failed distinction, one-shot token reload on 401, per-call agent discovery, and workspace-constrained file ingestion. Adapt endpoint paths, header names, and the env-var protocol to your infra. Omit FastMCP specifics if your MCP framework differs — keep the contract shapes.
