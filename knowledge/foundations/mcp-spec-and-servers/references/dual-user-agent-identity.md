<!-- capsule-v2 -->
# Dual user-agent identity — how should outbound requests self-identify differently for agent-initiated vs human-initiated actions?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** where does a server declare WHO initiated an outbound request, and which surface gets which identity?

## Two UA constants differing only in the parenthetical qualifier; identity chosen by initiation mode, not destination
**Path/Symbol:** `src/fetch/src/mcp_server_fetch/server.py` — constants :23–24; closure wiring in `serve` :194–195; autonomous-UA call sites :80 (robots GET) and :124 via `fetch_url` from `call_tool` :237–239; manual-UA call site :265 (prompt path only).
**Signature:** module constants `DEFAULT_USER_AGENT_AUTONOMOUS` / `DEFAULT_USER_AGENT_MANUAL`; `serve(custom_user_agent: str | None = None, ignore_robots_txt: bool = False, proxy_url: str | None = None)` binds `user_agent_autonomous = custom_user_agent or DEFAULT_USER_AGENT_AUTONOMOUS` and `user_agent_manual = custom_user_agent or DEFAULT_USER_AGENT_MANUAL`.
**Data Shape:** the two defaults are byte-identical except one parenthetical: `ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)` vs `ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)`. Both collapse to ONE string when `custom_user_agent` is supplied.

### Decisive source
```python
# server.py:23-24
DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"

# server.py:194-195 — override collapses the distinction
    user_agent_autonomous = custom_user_agent or DEFAULT_USER_AGENT_AUTONOMOUS
    user_agent_manual = custom_user_agent or DEFAULT_USER_AGENT_MANUAL
```

**Flow:** startup resolves two identities from at most three inputs (`custom or AUTONOMOUS`, `custom or MANUAL`) → every request on the TOOL surface carries the AUTONOMOUS identity: the robots.txt consent GET (:80) and the page fetch that follows it (:124, reached only from `call_tool`) → requests on the PROMPT surface (human typed the URL into their UI) carry the USER-SPECIFIED identity (:265) and run NO robots gate at all — consent guards only the autonomous surface, because a human asking for a specific page IS the authorization.
**Invariant:** identity is selected by INITIATION MODE, never by destination or URL shape; remote sites can therefore distinguish agentic traffic from user-directed traffic in their logs/rate-limiters/robots policies, and the parenthetical qualifier makes that claim honest rather than cosmetic. The robots evaluation itself always runs under the autonomous identity even though it precedes the fetch — policy lookup and action share one declared actor.
**Probe:** `src/fetch/tests/test_server.py` imports `DEFAULT_USER_AGENT_AUTONOMOUS` (:12) and threads it through every `TestCheckMayAutonomouslyFetchUrl` / `TestFetchUrl` case (:95–326), pinning the autonomous path end-to-end. Honest coverage caveat: the MANUAL half has NO direct upstream test — `get_prompt` is untested in this suite (confirmed by full test-file read: imports list contains no manual constant and no serve/get_prompt symbols); the split above is source-read evidence at :194–195/:265.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "user_agent_autonomous user_agent_manual DEFAULT_USER_AGENT serve" });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.fetch.src.mcp_server_fetch.server.serve" });
```
(Live-executed at `599dafc1`: search_graph enumerated all fetch functions with serve :181–288; snippet resolved serve byte-consistent with disk.)

## Verdict
Adopt mode-scoped outbound identities: derive per-initiation-mode UA strings at startup from optional overrides, attach the machine identity to consent lookups AND the actions they authorize, and reserve the human-declared identity for surfaces a human drives directly — then let the human-driven surface skip consent gates designed for autonomous action. Keep the distinction inside one honest qualifier so overrides remain possible. Adapt the qualifier text and header set to your product; omit nothing structurally — collapsing to a single identity erases exactly the signal sites use to rate-limit agents separately from users. Coverage caveat recorded above: manual-path behavior rests on source reading only at `599dafc1`.
