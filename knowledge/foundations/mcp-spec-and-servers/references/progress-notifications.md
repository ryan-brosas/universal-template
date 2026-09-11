<!-- capsule-v2 -->
# Progress notifications — how does a long-running tool stream step updates without spamming clients that never asked?

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** What is the opt-in gate and the correct notification emission for multi-step tool work?

## progressToken presence gates every notifications/progress emission
**Path/Symbol:** `src/everything/tools/trigger-long-running-operation.ts:registerTriggerLongRunningOperationTool` (:42–82 — schema with defaults :6–12, step loop + gated notification :50–70); spec anchor `schema/draft/schema.ts` (`ProgressNotificationParams` :1009–1038, reserved `_meta.progressToken` key basic/index.mdx :350–352).

**Signature:** handler `(args, extra) => Promise<CallToolResult>`; inside: `const progressToken = extra._meta?.progressToken;` then per step `server.server.notification({method: "notifications/progress", params: {progress: i, total: steps, progressToken}}, {relatedRequestId: extra.requestId})`.

### Decisive source
```ts
// src/everything/tools/trigger-long-running-operation.ts:50-69
const progressToken = extra._meta?.progressToken;
for (let i = 1; i < steps + 1; i++) {
  await new Promise((resolve) => setTimeout(resolve, stepDuration * 1000));
  if (progressToken !== undefined) {        // opt-in gate
    await server.server.notification(
      {
        method: "notifications/progress",
        params: { progress: i, total: steps, progressToken },
      },
      { relatedRequestId: extra.requestId } // correlate to the request
    );
  }
}
```
Spec contract (basic/index.mdx reserved keys + schema doc comments): `progressToken` in a request's `_meta` opts that request into out-of-band `notifications/progress`; the receiver is NOT obligated to emit them, but when it does the token MUST be echoed in each notification so the client can route it, and HTTP delivery rides the originating request's response SSE stream only.

**Flow:** client includes `_meta.progressToken` in tools/call → server divides duration by steps → after each awaited step emits `{progress, total, progressToken}` correlated via `relatedRequestId` → final CallToolResult summarizes. Without the token the identical loop runs silently and only the final result returns.

**Invariant:** no token ⇒ zero progress traffic (the receiver "is not obligated" and unrequested notifications violate the subscription/request-scoping rules); every emitted notification carries the caller's exact token. Porters who broadcast progress globally or drop `relatedRequestId` break multiplexed clients correlating streams.

**Probe:** `src/everything/__tests__/tools.test.ts::"should send progress notifications when progressToken provided"` (:345–364 — asserts `mockServer.server.notification` called EXACTLY steps times with `method: 'notifications/progress'` and the passed token, using 0.1s/2-step timing); companion test :329–343 pins completion text.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "progressToken notifications progress relatedRequestId long running", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt token-gated per-step progress with echo + request correlation; adapt your step granularity and pacing; omit the artificial sleep obviously — the portable skeleton is the gate-emit-correlate triple.
