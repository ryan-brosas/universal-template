<!-- capsule-v2 -->
# StreamEventBroadcaster payload discipline — which agent stream events reach the browser, and in what shape?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** how are raw provider stream events slimmed to a Reverb-safe UI contract without leaking tool payloads?

## Read-results dropped, pending-action data echo stripped, BroadcastException swallowed
**Path/Symbol:** `packages/Chat/src/Support/StreamEventBroadcaster.php:broadcast/payloadFor/payloadForToolResult/payloadForToolCall` (:28-117).
**Signature:** `broadcast(StreamEvent $event): void`; static `payloadFor(StreamEvent $event): ?array{as: string, with: array<string,mixed>}|null`.
**Data Shape:** outgoing envelope `{as: eventType, with: payload}`; ToolResult events re-encoded from the decoded JSON of `toolResult->result`; ToolCall events reduced to `{invocation_id, tool_name}`.

### Decisive source
```php
$decoded = json_decode((string) $raw, true);
if (! is_array($decoded) || ($decoded['type'] ?? null) !== 'pending_action') {
    return null;                       // ALL read-tool results: dropped entirely
}
unset($decoded['data']);               // heavy proposal payload stripped; card fetched server-side
```
```php
} catch (BroadcastException $e) {
    ChatTelemetry::breadcrumb('stream.broadcast_dropped', [...]);   // Reverb 10 KB cap — never kills the turn
}
```

**Flow:** each stream event → payloadFor classification: non-tool events pass through as-is; ToolCall slimmed to name+invocation (arguments stay server-side); ToolResult decoded — anything not typed `pending_action` (i.e., every READ tool) returns null and is silently dropped; pending_action results keep identity/status fields but lose their `data` body. Broadcast failures degrade to telemetry breadcrumbs.
**Invariant:** the browser can render turn progress but can NEVER reconstruct CRM records or tool arguments from the wire — heavy data reaches the client through authenticated server-side fetches, not the broadcast channel. The type check runs on decoded JSON, so a result whose string value merely contains "pending_action" is not misclassified (test-pinned).
**Probe:** `tests/Feature/Chat/StreamEventBroadcasterTest.php` (:16 read results skipped, :37 data echo stripped, :72 no literal-string misclassification, :99 tool_call slimmed); `BroadcastReverbConfigTest.php` (channel config).
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "StreamEventBroadcaster payloadForToolResult payloadFor", limit: 6, fields: ["signature", "lines"] });
```

## Verdict
Adopt: classify-then-slim broadcast discipline with drop-by-default for read payloads and swallow-and-log transport errors, whenever proxying agent streams to browsers. Adapt event taxonomy to your SDK. Omit Reverb-specific size constants.
