<!-- capsule-v2 -->
# ACP stream capture — how do you preserve raw wire fidelity when a validating SDK strips undeclared fields?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The ACP bridge pipes the agent's ndjson stream through the ACP SDK, which validates `session/update` notifications and drops fields the schema does not declare — but the host needs the raw payload (e.g. a draft programmatic `name` on a tool_call) for lossless replay and audit. How do you keep both the validated stream AND the raw bytes, re-associating them later?

## Ordered raw-fidelity sidecar over a TransformStream
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/acp-stream-capture.ts` — `captureACPStream` (:36–91), `getRawSessionUpdate` (:93–111), `sessionUpdatesMatch` (:113–137), `KNOWN_SESSION_UPDATES` (:7–19); wiring `bridge/index.ts` :416–434 (capture over `acp.ndJsonStream`), :288–316 (takeForUpdate per validated update + drainRawValues on error), :539–541 (drain on cold-restore history discard).
**Signature:** `captureACPStream({ stream }: { stream: ACPStream }): { stream: ACPStream; capture: ACPStreamCapture }`; `takeForUpdate({ update }): { precedingRawValues: ReadonlyArray<unknown>; rawUpdate: unknown }`; `drainRawValues(): ReadonlyArray<unknown>`.
**Data Shape:** sidecar = ordered array of `{ rawUpdate: unknown; forwarded: boolean }`. Forwarding rule: a notification is inspected only when `method === 'session/update'` with record params; `canFilterUnknown` requires a string `sessionId` and a record `update` — malformed notifications are ALWAYS forwarded (SDK validation owns the error). A well-formed update is forwarded iff its `sessionUpdate` discriminant is in the 15-member KNOWN_SESSION_UPDATES set (user/agent/thought chunks, tool_call(+update), plan/plan_update/plan_removed, available_commands_update, current_mode_update, config_option_update, session_info_update, usage_update).

### Decisive source
```ts
// acp-stream-capture.ts:43–60 — record raw before forwarding, filter unknown only when well-formed
transform(message, controller) {
  const rawUpdate = getRawSessionUpdate({ message });
  if (!rawUpdate.isSessionUpdate) { controller.enqueue(message); return; }
  const sessionUpdate = getStringProperty({ value: rawUpdate.value, property: 'sessionUpdate' });
  const forwarded =
    !rawUpdate.canFilterUnknown ||
    sessionUpdate == null ||
    KNOWN_SESSION_UPDATES.has(sessionUpdate);
  updates.push({ rawUpdate: rawUpdate.value, forwarded });
  if (forwarded) controller.enqueue(message);
},
```

**Flow:** every message flows through the pipe: non-session/update messages pass untouched; session/update notifications are recorded in the sidecar (raw value + forwarded flag) and either forwarded or filtered. Downstream, after the SDK validates and hands back a typed `SessionUpdate`, `takeForUpdate` scans the sidecar for the first FORWARDED entry matching the validated update (discriminant equality, plus `toolCallId` for tool_call kinds and `messageId` for the three chunk kinds), splices out entries `0..index`, and returns the matched raw twin plus everything before it as `precedingRawValues` — so extension updates that arrived earlier in the same turn ride along in order. No match ⇒ the validated update itself stands in as its own raw value. `drainRawValues` empties the sidecar unconditionally.
**Invariant:** the validated stream is never reordered or duplicated — filtering only REMOVES unknown-discriminant updates from a well-formed notification; raw fidelity is total (every session/update raw value is captured exactly once, in arrival order); raw/validated re-association is prefix-consuming so each sidecar entry is returned at most once; malformed notifications are never filtered (fail-open to SDK validation, fail-closed to raw capture); on stream error the bridge drains the sidecar and emits everything raw before closing, so a turn that dies mid-stream still surfaces what the agent actually sent.
**Probe:** `bridge/acp-stream-capture.test.ts` (178L, 5 cases) — pins draft-field preservation (tool_call with undeclared `name` survives in rawUpdate while the validated stream carries the SDK-stripped shape), unknown-discriminant filtering with sidecar preservation, extension-before-known ordering (`precedingRawValues` returns the extension first), malformed-known forwarding, and the no-filter rule for notifications with non-string sessionId (:129–160).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "captureACPStream takeForUpdate drainRawValues KNOWN_SESSION_UPDATES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sidecar pattern whenever a validating boundary (SDK, zod parse, codegen client) strips fields you still owe a consumer: capture raw at the boundary, forward the validated view, and re-associate by a stable identity key with prefix-consuming splices so earlier extension records ride along in order. Adopt the fail-open forwarding rule for malformed input (let the validator own the error, keep the raw copy) and the drain-on-error flush (emit raw before closing a failed stream). Adapt the identity keys to your protocol (toolCallId/messageId here); omit the capture layer where no field stripping occurs or where raw replay is not required. Coverage caveat: fully test-pinned (5 cases); no graph-MCP coverage check this session (MCP absent — direct source+test fallback per AGENTS.md).
