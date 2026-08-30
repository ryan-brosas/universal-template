<!-- capsule-v2 -->
# ChatAgent MCP-session lifecycle — how does a chat agent survive a dead SSE session mid-conversation?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is an MCP-over-SSE client session validated, reconnected, and retried exactly once, and what does the knowledge-aware runtime context rebuild every turn?

## Validate → reconnect-once → retry, per call
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/chat/chat_agent/chat_agent.py:ChatAgent._is_session_valid` (:306-318), `execute_tool` (:320-355), `invoke` (:357-382), `setup` (:99-164).
**Signature:** `_is_session_valid() -> bool`; `execute_tool(tool_call: ToolCall)`; `invoke(chat_messages: List[BaseMessage], state: AgentState)`.
**Data Shape:** session validity probed via private attrs (`session._write_stream._state.open_send_channels > 0`) — no public API exists; retry trigger is TYPE-NAME string match `"ClosedResourceError" in str(type(e))`.

### Decisive source
```python
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    if not self.use_regular_chat and "ClosedResourceError" in str(type(e)):
                        logger.info("Attempting to reconnect due to closed resource error...")
                        await self.setup()
                        for fresh_tool in self.tools or self.base_tools or []:
                            if fresh_tool.name == tool_name:
                                return await fresh_tool.ainvoke(tool_args)
                    raise e
```

**Flow:** setup() probes `http://localhost:{server_ports.saved_flows}/sse` with a 5s aiohttp GET; unavailable or `save_reuse` off ⇒ legacy regular-chat mode (single `execute_task` tool). MCP mode enters sse_client + ClientSession contexts (kept as objects for later `__aexit__`). EVERY invoke/execute first checks `_is_session_valid`, reconnects via full `await self.setup()` when stale, and on ClosedResourceError retries the operation ONCE against freshly loaded tools before re-raising.
**Invariant:** Reconnect = full setup() (tools reloaded from the server) — caching tool objects across reconnects would call dead sessions. Exactly ONE retry: a second failure propagates. cleanup() force-resets fields even when `__aexit__` raises. `_dedupe_tools` keeps FIRST occurrence by name when merging base+filesystem+knowledge tools.
**Probe:** Adjacent direct tests pin the mode toggle & knowledge gating (`tests/unit/test_chat_knowledge_mode.py`, `test_chat_agent_knowledge_toggle.py`). Deterministic: `grep -n "ClosedResourceError" src/cuga/backend/cuga_graph/nodes/chat/chat_agent/chat_agent.py` hits both retry sites (:345, :376).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ChatAgent _is_session_valid execute_tool ClosedResourceError setup", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt probe-by-internals session validation, reconnect-through-full-setup, and single-retry semantics for long-lived MCP/SSE clients. Adapt the availability probe URL/timeouts. Omit the legacy env-var execution toggle unless you carry both modes.
