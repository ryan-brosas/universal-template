<!-- capsule-v2 -->
# Daemon frontend stdio bridge — how do you bridge MCP stdio framing onto a daemon connection without losing cancellation or backpressuring forever?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the frontend owe the client for oversized input, cancellation notifications, and maintenance exits?

## Capacity backpressure without loss + exact-notification correlation + maintenance drain
**Path/Symbol:** `src/daemon/frontend.c` + tests/test_daemon_frontend.c:1076–1151 (`recognizes_exact_cancellation_notification`, `correlates_cancellation_to_exact_request`, `ignores_cancellation_text_in_string_content`, `rejects_non_notification_cancellation_shapes`), 1152 (`maintenance_exits_while_stdio_reader_is_blocked`), 1391 (`over_capacity_input_backpressures_without_loss`).
**Signature:** frontend loop bridging stdin frames ↔ daemon runtime application callbacks; frame ops from runtime.h (op-code flags, `CBM_DAEMON_RUNTIME_APPLICATION_PAYLOAD_MAX = MAX_FRAME_SIZE - 16`).
**Data Shape:** Cancellation recognized ONLY as a true notification with exact shape; text mentioning "cancelled" inside string content is ignored; non-notification shapes rejected. Oversized input lines backpressure rather than truncate. Maintenance stop drains while a blocked reader is interruptible.

### Decisive source
```c
TEST(daemon_frontend_recognizes_exact_cancellation_notification) { ... }
TEST(daemon_frontend_ignores_cancellation_text_in_string_content) { ... }
TEST(daemon_frontend_over_capacity_input_backpressures_without_loss) { ... }
TEST(daemon_frontend_maintenance_exits_while_stdio_reader_is_blocked) { ... }
```

**Flow:** read stdio line → validate frame size → forward to runtime with op flags → correlate responses by id; cancellation notifications matched exactly (see cancellation-scoping capsule) → on maintenance/stop signal, wake a blocked reader and exit after in-flight requests settle.
**Invariant:** Never parse semantics out of payload STRINGS; never drop oversized input silently — apply backpressure; shutdown must not depend on stdin producing data.
**Probe:** the five named tests above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "frontend", limit: 5 });
```

## Verdict
Adopt strict-shape notification handling + lossless backpressure + reader-interruptible shutdown for any stdio-to-socket bridge; adapt frame limits; pair with frozen wire envelopes.
