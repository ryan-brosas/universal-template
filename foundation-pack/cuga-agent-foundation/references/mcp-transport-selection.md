<!-- capsule-v2 -->
# MCP transport selection + secret-resolved stdio env — why does `/sse` in the URL pick the transport, and why is every env value resolved BEFORE subprocess spawn?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** One registry must launch stdio subprocesses, connect SSE endpoints, and speak streamable-HTTP — how is the transport chosen, and where do credentials get injected for each?

## Auto-detect transport ladder + per-transport auth injection + cwd anchoring
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py` — `_create_transport` :928-1031 (auto-detect :932-941: no type + command → stdio; no type + url → `'sse' if '/sse' in url else 'http'`; default stdio); stdio env resolution :953-962 (`resolve_secret` per string value, keep original when resolver returns None); cwd anchor :964-985 (`os.makedirs(exist_ok=True)` — failure falls through to loud subprocess error, never swallowed); auth application :998-1026 (`apply_authentication(auth, headers, query_params)` + `_merge_auth_query_params` :40-44 preserving existing query via `parse_qsl(keep_blank_values=True)`).
**Signature:** `StdioTransport(command, args, env=resolved_env, cwd=cwd_value)`; `SSETransport(url, headers=None)` / `StreamableHttpTransport(url, headers=None)` with query-param auth merged INTO the URL.
**Data Shape:** `ServiceConfig{transport?: 'stdio'|'sse'|'http'|None, command?, args?, env?, cwd?, url?, auth?}`; FastMCP availability is import-guarded (:13-20) — all four symbols None when the package is missing, and `_initialize_fastmcp_client` raises a human message.

### Decisive source
```python
# mcp_manager.py:953-962 — secrets resolve at TRANSPORT BUILD time, not call time
from cuga.backend.secrets import resolve_secret
raw_env = config.env or {}
resolved_env = {}
for k, v in raw_env.items():
    if isinstance(v, str):
        resolved = resolve_secret(v)
        resolved_env[k] = resolved if resolved is not None else v   # ← unresolved keeps literal
    else:
        resolved_env[k] = v
```
Resolving at spawn time means a rotated vault secret requires reconnect to take effect — deliberate: subprocess environments can't be mutated after launch, and a half-resolved env at spawn would be worse. The None-keeps-literal fallback lets plain values pass through untouched while `secret://`-style refs resolve.
```python
# mcp_manager.py:40-44 — auth params MERGE into an existing query string
def _merge_auth_query_params(base_url: str, auth_params: dict[str, str]) -> str:
    parsed = urlparse(base_url)
    merged = dict(parse_qsl(parsed.query, keep_blank_values=True))
    merged.update(auth_params)          # ← auth wins over pre-existing same-name param
    return parsed._replace(query=urlencode(merged, quote_via=quote)).geturl()
```
**Flow:** config → transport type (explicit or auto-detected) → build transport object (validating required fields per type with actionable errors like `"STDIO transport requires 'command' for {name}"`) → client connects → tools listed → transports RETAINED in `mcp_transports[name]` so later tool calls reuse them (:1140-1149); fallback path posts directly to `{base_url}/call_tool` when no transport object exists (:1162-1194).
**Invariant:** The URL-substring SSE heuristic (`'/sse' in config.url`) is load-bearing for configs that omit `transport:` — changing endpoint naming conventions silently flips servers to streamable-HTTP. Auth must be applied at BOTH connect time (transport headers/query) and call time (`_call_mcp_server_tool` re-applies from `auth_config`). Never pass unresolved secret references into a spawned process environment.
**Probe:** direct tests `mcp_manager/tests/test_sse_auth.py` (SSE+auth header/query wiring, 352L suite). Coverage caveat: stdio env-resolution branch untested upstream (needs subprocess + secrets backend) — verify by reading :953-985.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_create_transport StdioTransport SSETransport StreamableHttpTransport apply_authentication", limit: 10 });`

## Verdict
Adopt the auto-detect ladder with explicit-field validation errors, spawn-time secret resolution with literal passthrough, and URL-merging query auth. Adapt detection heuristics to your endpoint conventions. Omit the raw `/call_tool` HTTP fallback if you always hold live transports.
