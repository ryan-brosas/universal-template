<!-- capsule-v2 -->
# MCP server surface — 12 tools + 5 resources over the kernel with dataclass-to-JSON discipline

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does a FastMCP server expose an audit kernel so agent clients get structured, honest output?

## Tool wrappers = normalize URL → call core → asdict JSON
**Path/Symbol:** `src/geo_optimizer/mcp/server.py:mcp` (36), `geo_audit` (67–99), `geo_check_bots` (396+), `_to_json` (50–55).
**Signature:** `@mcp.tool() def geo_audit(url: str) -> str` (plus geo_fix, geo_llms_generate, geo_citability, geo_schema_validate, geo_compare(urls), geo_gap_analysis(url1, url2), geo_ai_discovery, geo_check_bots, geo_trust_score, geo_negative_signals, geo_factual_accuracy); resources `geo://ai-bots`, `geo://score-bands`, `geo://methods` (dynamic from CITABILITY_METHODS), `geo://changelog`, `geo://ai-discovery-spec`.
**Data Shape:** every tool returns pretty `json.dumps(asdict(dataclass))` (`ensure_ascii=False`, `default=str`) — never prose.

### Decisive source
```python
def _to_json(data: object) -> str:
    if hasattr(data, "__dataclass_fields__"):
        data = asdict(data)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)

def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url        # same normalization as run_full_audit
```

**Flow:** each tool mirrors one kernel entry point (`run_full_audit`, `run_all_fixes`, `generate_llms_txt`, `audit_citability`, `validate_jsonld`, gap/diff analysis) → errors surface inside the payload (AuditResult.error / skipped_reason) rather than as tool exceptions, matching the error-as-value convention of the core. The skill catalog's validator cross-checks these tool names via AST (see skill-catalog capsule) keeping spec ↔ server in lockstep.
**Invariant:** Tools are thin: no business logic beyond URL normalization; response schema stability is guarded by tests/test_audit_contract fixtures — adding fields is additive-safe, renaming breaks clients. Resource endpoints expose the CONFIG tables (bots, bands, methods) so agents can read the rubric without source access.
**Probe:** `tests/test_mcp_server.py::test_geo_audit_tool_returns_json_contract` (+ per-tool suites; blocked at this lane's pin by optional-dep install gate — see leaf Provenance; deterministic contract evidence via `tests/test_audit_contract.py` green).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "mcp server tools geo_audit", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt thin-asdict-tool + config-as-resource shaping for any MCP exposure of a Python kernel; adapt tool set; omit changelog resource if unmaintained.
