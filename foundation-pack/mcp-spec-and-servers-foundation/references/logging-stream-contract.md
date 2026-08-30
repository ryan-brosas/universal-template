<!-- capsule-v2 -->
# Logging stream contract — how does a client opt in to `notifications/message`, and where may the server send them?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact opt-in, scoping, and error contract for server→client structured log messages?

## Request-scoped logging via `_meta` logLevel (deprecated SEP-2577)
**Path/Symbol:** `schema/draft/schema.ts` — `LoggingMessageNotificationParams` :2031–2044, `LoggingMessageNotification` :2058–2061 (`method: "notifications/message"`), `LoggingLevel` :2075–2083; opt-in key: `RequestMetaObject["io.modelcontextprotocol/logLevel"]` :100–110; prose: `docs/specification/draft/server/utilities/logging.mdx` whole.
**Signature:** `interface LoggingMessageNotificationParams extends NotificationParams { level: LoggingLevel; logger?: string; data: unknown }`; `type LoggingLevel = "debug"|"info"|"notice"|"warning"|"error"|"critical"|"alert"|"emergency"`.
**Data Shape:** `data` is ANY JSON-serializable value; `logger` is an optional free-form source name; notifications ride the response stream of the request that set the level.

### Decisive source
```ts
// schema.ts:100-104 — the opt-in gate (a porter who logs unconditionally
// breaks the contract):
//   The desired log level for this request. Optional.
//   If absent, the server MUST NOT send any notifications/message for this
//   request. The client opts in to log messages by explicitly setting a
//   level. Replaces the former `logging/setLevel` RPC.
// logging.mdx (Requesting Log Messages): when present, the server MAY send
//   notifications at or above the requested level ON THE RESPONSE STREAM of
//   that request, before the final response; it MUST NOT deliver them on a
//   subscriptions/listen stream or any other stream.
// logging.mdx (Error Handling): unrecognized logLevel value => reject with
//   -32602 Invalid params.
```

**Flow:** request arrives with `_meta["io.modelcontextprotocol/logLevel"]` set → server filters its log emissions to severity ≥ requested level → emits `notifications/message` only on that request's own stream and only before the final response → absent key = total silence on that request. RFC-5424 syslog ordering governs severity comparisons.
**Invariant:** logging is REQUEST-SCOPED, never session-scoped or broadcast — there is no `logging/setLevel` RPC anymore and no cross-request sticky state; emitting on a subscription stream is a protocol violation. Servers declaring the capability advertise `logging: {}` in ServerCapabilities (:808). Whole feature is DEPRECATED as of 2026-07-28 (SEP-2577): migrate to stderr (stdio) or OpenTelemetry; adopt only for legacy-client interop within the 12-month window.
**Probe:** direct test lives in the servers repo: `servers/src/everything/server/logging.ts` sends through `server.sendLoggingMessage(...)` ("we ensure that the client's chosen logging level will be respected", :45–47) driven by `toggle-simulated-logging`; session-keyed interval map with `stopSimulatedLogging` cleanup exercised via the factory cleanup path in `__tests__/server.test.ts`. Spec-side caveat: no runtime tests in the spec repo.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "LoggingMessageNotification LoggingLevel logLevel notifications/message", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-request `_meta` opt-in gate, response-stream-only delivery, and `-32602` rejection of unknown levels; adapt message volume/rate-limiting and logger naming to your stack; omit new-implementation adoption entirely — the feature is deprecated SEP-2577; build on stderr/OpenTelemetry instead and use this contract solely for legacy interop.
