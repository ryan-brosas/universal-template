<!-- capsule-v2 -->
# await_human Long-Poll Loop — how does a blocking-on-human call survive gateways and map every terminal state?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the exact reconnect/timeout/status contract the SDK poller must implement to port `await_human()` faithfully?

## Reconnecting long-poll over four terminal states
**Path/Symbol:** `packages/python/awaithumans/client.py:_poll_until_terminal` (:211–269) + entry `await_human` (:93–208); TS twin `packages/typescript-sdk/src/await-human.ts:pollUntilTerminal`.
**Signature:** `_poll_until_terminal(base_url, task_id, task_description, timeout_seconds, response_schema, auth_headers) -> T`.
**Data Shape:** GET `/api/tasks/{id}/poll?timeout=25`; client httpx timeout = POLL_INTERVAL_SECONDS(25) + buffer(10); non-terminal body ⇒ loop again forever until a terminal branch returns/throws.

### Decisive source
```python
async with httpx.AsyncClient(timeout=POLL_INTERVAL_SECONDS + SDK_POLL_TIMEOUT_BUFFER_SECONDS) as client:
    while True:
        resp = await client.get(f"{base_url}/api/tasks/{task_id}/poll",
                                params={"timeout": POLL_INTERVAL_SECONDS}, headers=auth_headers)
        if resp.status_code == 404: raise TaskNotFoundError(task_id)
        if resp.status_code != 200: raise PollError(task_id, resp.status_code, resp.text)
        status = resp.json()["status"]
        if status == "completed":
            try:    return response_schema.model_validate(resp.json()["response"])
            except Exception as e: raise SchemaValidationError("response", str(e)) from e
        if status == "timed_out":   raise TaskTimeoutError(task_description, timeout_seconds)
        if status == "cancelled":   raise TaskCancelledError(task_description)
        if status == "verification_exhausted":
            raise VerificationExhaustedError(task_description, poll_data.get("verification_attempt", 0))
```

**Flow:** validate range (60s…30d ⇒ `TimeoutRangeError`) → validate payload against schema client-side → POST create (ConnectError ⇒ typed `ServerUnreachableError`, non-200/201 ⇒ `TaskCreateError`) → print stderr waiting banner (logger.info would VANISH — user scripts have no handlers; stderr keeps stdout pipeable) → reconnect-every-25s poll loop → typed raise/validated return per status.
**Invariant:** the server holds each poll ≤25s (under the 30/60s gateway-kill window) then answers with current status; the CLIENT owns the overall deadline by raising on `timed_out`. Response validation failure is a distinct `SchemaValidationError(field="response")` — never silently return untyped data.
**Invariant (import):** httpx is imported INSIDE the function (:164–168) because its transitive `urllib.request` is forbidden by Temporal workflow sandboxes at replay time — keep heavy imports out of module top level if your SDK also rides durable engines.
**Probe:** `packages/typescript-sdk/tests/await-human.test.ts` (:91–121 range/payload/marketplace rejects, :123–170 well-formed POST + validated response, :171–185 non-terminal reconnect, :415–445 typed terminal throws); Python mirror behavior pinned by server-side poll route tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_poll_until_terminal long poll", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 25s+buffer reconnect cadence, the four-way typed terminal mapping, client-side schema validation before returning, stderr progress banners, and sandbox-safe deferred imports. Adapt transport (fetch vs httpx) and constant names (MIN/MAX_TIMEOUT_MS vs _SECONDS — both pinned in each SDK's constants module). Omit the AwaitVerify managed poll (24h floor, different endpoint family).
