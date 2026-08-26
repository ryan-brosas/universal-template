<!-- capsule-v2 -->
# A2A SDK-vs-legacy transport duality — dual card-shape URL ladder and honest failure-status mapping

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your agent federation must speak A2A v0.3 JSON-RPC over HTTP while still supporting sse/websocket/stdio peers, across TWO agent-card wire shapes (pydantic v0.3 vs protobuf v1.0). How do you pick the RPC endpoint from either card shape — and how does a peer's failed execution stay distinguishable from a transport success?

## The protocol contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/a2a_protocol.py` (`HAS_A2A_SDK` try-import gate :20-33, `_extract_text_from_task` :36-57, `fetch_agent_card` :115-140, `_agent_card_rpc_url` :143-188, `delegate_task_via_a2a_sdk` :191-255, legacy `A2AProtocol` class :258-494).
**Signature:** `fetch_agent_card(base_url, auth=None, timeout=30.0) -> AgentCard`; `delegate_task_via_a2a_sdk(agent_card, task, auth=None, timeout=30.0, variables=None, rpc_url=None) -> {"result": str, "variables": dict, "status": "success"|"failed"}`.
**Data Shape:** SDK path = raw JSON-RPC 2.0 `message/send` with `{role:"user", parts:[{kind:"text", text:task}], messageId: uuid4().hex}`; optional variables ride as `params.metadata={"variables": ...}` (the A2A variables extension). Legacy path = custom envelopes `{protocol_version:"1.0", message_type:"task_delegation"|"result_sharing"|"capability_query"|"status_query", from_agent:"supervisor", to_agent:...}`.

### Decisive source
```python
# :143-160 docstring — the two card shapes the URL ladder must bridge
# - v0.3 pydantic (`a2a.compat.v0_3.types.AgentCard`) — has a top-level `url`
# - v1.0 protobuf (what A2ACardResolver.get_agent_card returns on SDK 1.x).
#   No top-level url; the URL lives in supported_interfaces[0].url along with a
#   protocol_binding ("JSONRPC", "GRPC", ...)

# :164-181 — prefer JSONRPC binding; NEVER fall through to a grpc:// URL
for iface in getattr(agent_card, "supported_interfaces", None) or []:
    if binding == "JSONRPC": url = iface_url; break
    if not http_fallback and iface_url.lower().startswith(("http://", "https://")):
        http_fallback = iface_url

# :186-188 — append /a2a unless already on a recognized transport path
if any(url.endswith(p) for p in ("/a2a", "/jsonrpc", "/rpc")):
    return url
return f"{url}/a2a"

# :244-246 — a 200 without a Task envelope is a FAILURE, not an empty result
# The peer answered 200 but with no recognizable Task envelope —
# treat as a transport-level failure rather than silently flattening.
raise RuntimeError("A2A response is missing a valid `result` task envelope")

# :253 — honest status: remote execution error ⇒ status="failed" even on HTTP 200
normalized_status = "failed" if ("fail" in state or "error" in state) else "success"
```

**Flow:** prepare-time fetches cards once per external HTTP agent (`A2ACardResolver` + bearer header); delegation prefers the SDK path when `agent_card and HAS_A2A_SDK and transport=="http"`, else legacy `A2AProtocol.connect()/delegate_task()/disconnect()` per call (finally-disconnect). Text extraction walks the returned Task's history BACKWARD preferring role=="agent" messages, then status.message, else "". Legacy transports degrade honestly: stdio delegate returns a MOCK response with a loud warning; capability/status queries return `[]` / `{"status":"unknown"}` on failure instead of raising.
**Invariant:** never POST to a non-HTTP interface URL even when it is interfaces[0] — pick JSONRPC-bound first, HTTP-scheme fallback second, base-url last. Transport success ≠ execution success: the caller-visible `status` maps peer TaskState fail/error words to `"failed"` so upstream can retry/distinguish. Missing envelope on HTTP 200 raises rather than silently flattening to empty text. The whole module degrades gracefully when a2a-sdk isn't installed (`HAS_A2A_SDK=False` sentinel types).

**Probe:** no direct unit test pins `_agent_card_rpc_url`/status-mapping — COVERAGE CAVEAT; the delegation layer above IS test-pinned via `test_delegation_recording.py::test_a2a_sdk_variable_forwarding` (:311-321, mocks `delegate_task_via_a2a_sdk`). Deterministic probes: source needles verbatim; graph retrieval below.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_agent_card_rpc_url supported_interfaces protocol_binding delegate_task_via_a2a_sdk _extract_text_from_task HAS_A2A_SDK", limit: 10 });
```

## Verdict
Adopt the dual-card-shape URL ladder (JSONRPC-binding preference + scheme filter + transport-path suffix guard) and the success/failed status split for ANY A2A-style federation client; adopt backward-history text extraction for Task envelopes. Adapt message-type names on the legacy path to your protocol. Omit stdio mock only when you have no local-agent story.
