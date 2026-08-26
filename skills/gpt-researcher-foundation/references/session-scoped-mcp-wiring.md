<!-- capsule-v2 -->
# Session-scoped MCP wiring — why must per-request MCP configs never touch os.environ?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How does one research session add an MCP retriever without leaking its settings into every later request in the same process?

## _process_mcp_configs cfg-only mutation
**Path/Symbol:** `gpt_researcher/agent.py:283-309` (`_process_mcp_configs`), strategy back-compat resolver `agent.py:217-281` (`_resolve_mcp_strategy`).
**Signature:** `def _process_mcp_configs(self, mcp_configs: list[dict]) -> None`
**Data Shape:** Mutates `self.cfg.retrievers` (list of names) by appending `"mcp"` if absent; stores configs on the instance. Docstring cites issue #1676 (process-level env pollution).

### Decisive source
```python
# Add MCP to retrievers via cfg (not os.environ) to avoid env pollution.
if hasattr(self.cfg, 'retrievers') and self.cfg.retrievers:
    current_retrievers = (
        list(self.cfg.retrievers) if isinstance(self.cfg.retrievers, list)
        else [r.strip() for r in str(self.cfg.retrievers).split(",") if r.strip()]
    )
    if "mcp" not in current_retrievers:
        current_retrievers.append("mcp")
        self.cfg.retrievers = current_retrievers
```

**Flow:** constructor receives `mcp_configs` → appends "mcp" to THIS instance's retriever list → `_resolve_mcp_strategy` maps legacy knobs (`mcp_max_iterations` 0/1/-1 → disabled/fast/deep; "optimized"/"comprehensive" → fast/deep with deprecation warnings) → deep research propagates BOTH `mcp_configs` and `mcp_strategy` into child researchers (`deep_research.py:443-445`) so nested passes keep MCP behavior.
**Invariant:** env vars are process-global; a server backend serving concurrent users must scope everything per-instance — verified structurally: no `os.environ` reference anywhere inside `_process_mcp_configs`.
**Probe:** battery P11a-b GREEN via AST walk proving zero `os.environ` attributes in the function body.
