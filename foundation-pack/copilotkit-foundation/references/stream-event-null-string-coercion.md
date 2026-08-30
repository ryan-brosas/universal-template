<!-- capsule-v2 -->
# stream-event-null-string-coercion

## Source
- Repo: `copilotkit`
- Path: `packages/channels-slack/src/sanitizing-http-agent.ts`
- Symbol: `SanitizingHttpAgent` / `coerceNullStrings`
- Lines: 36-65
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-slack.src.sanitizing-http-agent.SanitizingHttpAgent`

## Signature & Data Shape
```typescript
export class SanitizingHttpAgent extends HttpAgent {
  run(input: RunAgentInput): Observable<BaseEvent>;
}

function coerceNullStrings(event: unknown): unknown;
```

## Decisive Source Excerpt
```typescript
export class SanitizingHttpAgent extends HttpAgent {
  run(input: RunAgentInput): Observable<BaseEvent> {
    return parseSSEStream(
      runHttpRequest(() => this.fetch(this.url, this.requestInit(input))),
      this.debugLogger,
    ).pipe(map((event: unknown) => coerceNullStrings(event) as BaseEvent));
  }
}

let coercionWarned = false;

function coerceNullStrings(event: unknown): unknown {
  if (!event || typeof event !== "object") return event;
  const e = event as Record<string, unknown>;
  if (e["parentMessageId"] === null) {
    e["parentMessageId"] = "";
    if (!coercionWarned) {
      coercionWarned = true;
      console.warn(
        "SanitizingHttpAgent: coerced null parentMessageId to empty string",
      );
    }
  }
  return event;
}
```

## Flow
1. Receive incoming Server-Sent Events (SSE) from remote agent runtimes (e.g. LangGraph).
2. Intercept raw stream events prior to strict client-side Zod validation.
3. Check for specific nullable wire anomalies, such as `TOOL_CALL_START` events with `parentMessageId: null`.
4. Coerce `null` string fields into valid empty string `""` values.
5. Forward sanitized event objects to downstream UI stream subscribers.

## Invariant
Stream adapters must sanitize known runtime wire anomalies (e.g., `parentMessageId: null` on LangGraph tool interrupts) before strict schema validation to prevent spurious turn aborts on human-in-the-loop steps.

## Direct-Test Probe
- File: `packages/channels-core/src/sanitize-agent-events.test.ts`
- Lines: 15-45
- Suite: `describe("sanitize-agent-events")`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"SanitizingHttpAgent coerceNullStrings parentMessageId"}'
```

## Verdict
Adopt stream-level event coercion for external agent runtime integration.
