<!-- capsule-v2 -->
# Jupyter-wire executor family — how do Docker/Modal/Blaxel executors share one protocol with different sandboxes?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is the shared kernel-gateway choreography (auth token → readiness poll → kernel create → websocket channels), and what differs per backend?

## One wire protocol, four launchers
**Path/Symbol:** `src/smolagents/remote_executors.py` — module helpers `_websocket_send_execute_request` (:450-478) / `_websocket_run_code_raise_errors` (:481-529) / `_create_kernel_http` (:532-548); `DockerExecutor.__init__` (:572-677), `_wait_for_server` (:710-723); `ModalExecutor` (:726-856); `BlaxelExecutor` (:859-1076).
**Signature:** All run via `with closing(create_connection(self.ws_url)) as ws: return _websocket_run_code_raise_errors(code, ws, logger, allow_pickle)`; `CodeOutput(output, logs, is_final_answer)`.
**Data Shape:** Execute request = standard Jupyter msg v5.0 (`msg_type:"execute_request"`, `store_history:True`, `silent:False`, fresh uuid4 msg_id per call). Reply loop filters strictly by `parent_header.msg_id == ours`, then dispatches on msg_type: `stream`→logs, `execute_result`→text/plain result, `error`→FinalAnswerException routing or AgentError(traceback joined), `status:idle`→done.

### Decisive source
```python
# :502-507 — the correlation filter that keeps concurrent kernel chatter out:
while True:
    msg = json.loads(ws.recv())
    parent_msg_id = msg.get("parent_header", {}).get("msg_id")
    if parent_msg_id != msg_id:      # skip unrelated messages
        continue
# :664-668 — Docker launch tail; Modal/Blaxel repeat the same 3 steps over tunnels:
self._wait_for_server(token)
self.kernel_id = _create_kernel_http(f"{self.base_url}/api/kernels?token={token}", self.logger)
self.ws_url = f"ws://{host}:{port}/api/kernels/{self.kernel_id}/channels?token={token}"
```

**Flow:** Per backend the launcher differs but the choreography is identical: (1) mint `secrets.token_urlsafe(16)` and inject as `KG_AUTH_TOKEN` env (Docker env-dict merge handling list-form env; Modal as Secret.from_dict appended to user secrets; Blaxel in sandbox spec); (2) poll `/api/kernelspecs?token=` until 200 — Docker caps at 10×1s, Modal counts to >60 with a log every 10th then RuntimeError, Blaxel skips (fast-launch VMs); (3) POST /api/kernels requiring exactly HTTP 201 (failure logs status/headers/url/body/request-dump before raising); (4) open ws channels URL and run the message loop. Package installation is also code: `!pip install ...` executed through the same channel (Blaxel overrides with a process API + 600s poll and returns [] on failure instead of raising).
**Invariant:** The msg_id correlation filter is what makes one kernel reusable across sequential calls without response bleed. Backend differences are confined to transport (ws vs wss tunnel vs header-authenticated ws) and lifecycle cleanup (E2B `sandbox.kill()`, Docker stop+remove with delete()/`__del__` backstop, Modal terminate, Blaxel idempotent `_cleaned_up` flag).
**Probe:** `tests/test_remote_executors.py::TestDockerExecutorUnit.test_state_persistence/:test_execute_output/:test_syntax_error_handling` (:269-343), integration classes :386+. Live: FakeWS harness replaying stream/error/status frames keyed to the SENT msg_id → output/logs/is_final_answer split correctly, foreign-msgid frames ignored.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_websocket_run_code_raise_errors _create_kernel_http KG_AUTH_TOKEN kernelspecs", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the token→readiness→201-create→correlated-websocket choreography wholesale. Adapt only the launcher body for your sandbox provider. Omit Blaxel's process-API installer unless your backend can't execute shell lines through the kernel.
