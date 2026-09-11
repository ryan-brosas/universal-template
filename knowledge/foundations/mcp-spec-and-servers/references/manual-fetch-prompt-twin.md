<!-- capsule-v2 -->
# Manual fetch prompt twin — when the autonomous path refuses or fails, how does the human still get the content?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** how do you pair a gated tool with an ungated same-named prompt so every refusal has a concrete human escape hatch, and where do failures on each surface get delivered?

## Same-named Tool+Prompt pair; refusals route to the prompt; prompt-path errors become readable CONTENT, not protocol errors
**Path/Symbol:** `src/fetch/src/mcp_server_fetch/server.py` — `list_prompts` :209–221; refusal copy :90 and :107; `get_prompt` :257–284 (McpError catch :267–276); `raise_exceptions=False` :288.
**Signature:** `Prompt(name="fetch", arguments=[PromptArgument(name="url", required=True)])`; `get_prompt(name: str, arguments: dict | None) -> GetPromptResult`; tool handler returns `list[TextContent]`, prompt handler returns `GetPromptResult`.
**Data Shape:** both surfaces accept a bare URL string. The TOOL path raises `McpError` for transport/consent failures (protocol-visible error). The PROMPT path catches that same `McpError` and converts it into a SUCCESSFUL `GetPromptResult` whose single user-role message is the error text, with description `"Failed to fetch {url}"`.

### Decisive source
```python
# server.py:90 — every autonomous refusal ends by pointing at the twin surface
# "...the user can try manually fetching by using the fetch prompt"

# server.py:264-276 — the manual twin softens protocol errors into prompt content
        try:
            content, prefix = await fetch_url(url, user_agent_manual, proxy_url=proxy_url)
            # TODO: after SDK bug is addressed, don't catch the exception
        except McpError as e:
            return GetPromptResult(
                description=f"Failed to fetch {url}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=str(e)),
                    )
                ],
            )

# server.py:288 — handler exceptions must not kill the server process
        await server.run(read_stream, write_stream, options, raise_exceptions=False)
```

**Flow:** autonomous attempt fails (robots denial :100–108, robots.txt 401/403 :87–91, transport error, HTTP >=400) → the refusal message explicitly instructs the assistant to tell the user about "the fetch prompt" → the user invokes the SAME-NAMED prompt with the URL → the prompt path re-runs the shared pipeline under the manual identity with NO robots gate → success renders contents as one user-role PromptMessage; failure catches `McpError` and renders the error string the same way. Either way the HUMAN receives readable text in their UI instead of a JSON-RPC error frame.
**Invariant:** the escape hatch must EXIST (a registered prompt), be NAMED in every refusal message (the model can only route the user somewhere it was told about), and DELIVER its failures as content because prompts are rendered into a conversation, not handled by a client's error machinery. `raise_exceptions=False` complements this at process level: one bad request degrades to an error response, never to a dead stdio server. The TODO comment is part of the contract as shipped — the catch exists because an SDK bug mishandled raised errors on this path; porters on fixed SDKs may prefer raising, but must then verify their client renders it.
**Probe:** NO direct upstream test covers `get_prompt`, `list_prompts`, or `call_tool` (full test-file read: imports are the five module functions + `DEFAULT_USER_AGENT_AUTONOMOUS`; 20 tests all target module functions). Deterministic source checks recorded instead: refusal strings at :90/:107 both name the fetch prompt; the catch-and-convert block is :267–276; `raise_exceptions=False` at :288. Live suite (2026-08-25, 20/20 passed) proves the shared pipeline both surfaces call.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "get_prompt list_prompts GetPromptResult fetch prompt" });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.fetch.src.mcp_server_fetch.server.serve" });
```
(Live-executed at `599dafc1`: BM25 listed serve :181–288 and the fetch family; snippet byte-consistent with disk read of :209–288.)

## Verdict
Adopt the twin-surface pattern whenever an autonomous tool can refuse for policy reasons: register a same-named low-friction prompt, name that prompt inside every refusal message, run it without the autonomous-only gate, and deliver its failures as rendered content so a human always has a next step. Pair with non-fatal request handling (`raise_exceptions=False`-equivalent) so single failures never take the process down. Adapt which gate the prompt skips (robots here; your equivalent consent ladder there) and whether the catch remains needed given your SDK version. Omit nothing from the refusal-copy duty: an unnamed escape hatch is unreachable by the model. Coverage caveat: this seam is source-read evidence only — no upstream test pins the prompt surface at `599dafc1`.
