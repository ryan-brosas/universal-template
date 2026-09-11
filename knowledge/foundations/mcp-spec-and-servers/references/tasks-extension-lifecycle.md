<!-- capsule-v2 -->
# Tasks extension lifecycle — how do long-running operations return a durable handle instead of blocking, with mid-flight input?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What replaces the legacy `tasks/result` blocking call in the redesigned extension, and what must a server check before returning a task handle?

## Poll-with-tasks/get + tasks/update for mid-flight input
**Path/Symbol:** `docs/extensions/tasks/overview.mdx` (whole page; rationale :23–43; six-step flow :44–73; status table :124–135; client steps :149–202; server steps :204–262; negotiation mechanism :278). Legacy contrast: `CreateTaskResult` exists in `schema/2025-11-25/schema.ts`; the 2026-07-28 redesign moved tasks OUT of core into extension `io.modelcontextprotocol/tasks` (changelog.mdx major #6: replaces blocking `tasks/result` with polling via `tasks/get`, adds `tasks/update`, removes `tasks/list`, allows UNSOLICITED handles without per-request opt-in).

**Signature:** server returns `CreateTaskResult` (`resultType: "task"`) containing `taskId`, initial status, `ttlMs`, `pollIntervalMs`; client loops `tasks/get { taskId }` → response carries current status and, on terminal states, `result` (completed) or `error` (failed). Status machine: `working | input_required | completed | failed | cancelled`; last three are TERMINAL (:134–135 — "once reached, the task's state does not change").

### Decisive source
```md
# docs/extensions/tasks/overview.mdx — capability gate + mid-flight input
Before returning a `CreateTaskResult`, verify that the client included the
extension in its per-request capabilities. Never return a task to a client
that did not declare support.

If the task moves to `input_required`, read the `inputRequests` map, present
the requests to the user or model, and submit responses via `tasks/update`.
```
Status semantics (:126–132): `working` = in progress; `input_required` = server needs client input before continuing (see `inputRequests`); `completed` carries final output in `result`; `failed` carries JSON-RPC error in `error`; `cancelled` is "not always honored".

**Flow:** both sides advertise the extension (`io.modelcontextprotocol/tasks` in per-request `clientCapabilities.extensions` / in `server/discover` capabilities) → long-running request ⇒ server durably creates the task BEFORE sending the response (:240 "The task must be durably created before sending the response") → client polls `tasks/get` respecting `pollIntervalMs` → optional detour: `input_required` ⇒ client answers via `tasks/update { taskId, inputResponses }` (server acks empty; IGNORES responses for unknown or already-satisfied keys :250–254) → terminal poll returns result/error. `tasks/cancel` is COOPERATIVE: acknowledge always, honor when possible — the task may still reach a non-`cancelled` terminal status (:255–261, :71–73). Optional push updates ride `notifications/tasks` through `subscriptions/listen`, each carrying FULL task state (:137–145) — polling remains the default.

**Invariant:** never return a task handle to a client that did not declare the extension in THAT request's capabilities (per-request era rule); durable-create-before-respond means a crash after response-sent must still leave a resumable task — porters who create the record lazily break crash resilience (the whole point of durable IDs surviving disconnects/restarts :30–32, :197–201). Unknown-key tolerance in `tasks/update` makes retries idempotent.

**Probe:** no runtime tests in the spec repo (extension spec lives in modelcontextprotocol/ext-tasks); machine-checkable anchors: legacy `modelcontextprotocol.schema.2025-11-25.schema.CreateTaskResult` node in the graph (the redesigned shape lives in ext-tasks), plus `docs/specification/draft/server/discover.mdx` extension-advertisement example. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CreateTask", limit: 10 });
```

## Verdict
Adopt the five-status machine with terminal-state immutability, durable-create-before-response, capability-gated handle emission, unknown-key-tolerant `tasks/update`, and cooperative cancel semantics; adapt storage of task records to your host's persistence layer and the notification push cadence; omit legacy-core `tasks/list`/blocking `tasks/result` (removed in this revision).
