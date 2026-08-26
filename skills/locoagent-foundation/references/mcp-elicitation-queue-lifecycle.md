<!-- capsule-v2 -->
# Elicitation queue lifecycle — how does a server-initiated elicitation request reach the UI, honor hooks, and react to URL-completion notifications?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do I wire ElicitRequestSchema into app state with hook pre-resolution, abort safety, and a completion-notification phase flag?

## Hook-first resolution → state queue → abort-resolve → completion sets completed:true
**Path/Symbol:** `src/services/mcp/elicitationHandler.ts`: `registerElicitationHandler` (:68-212), queue event type `ElicitationRequestEvent` (:29-47), `findElicitationInQueue` (:54-66), completion notification handler (:175-207), hook runners `runElicitationHooks` (:214-257) / `runElicitationResultHooks` (:264-313).
**Signature:** `registerElicitationHandler(client: Client, serverName: string, setAppState): void` — registration wrapped in try/catch because setRequestHandler THROWS if the client wasn't created with the elicitation capability (:74-76).
**Data Shape:** Queue event `{serverName, requestId, params, signal, respond, waitingState?, onWaitingDismiss?, completed?}`; default waitingState for explicit-elicitationId requests `{actionLabel:'Skip confirmation'}` (:124-125).

### Decisive source
```ts
try {
  client.setRequestHandler(ElicitRequestSchema, async (request, extra) => {
    // Run elicitation hooks first - they can provide a response programmatically
    const hookResponse = await runElicitationHooks(serverName, request.params, extra.signal)
    if (hookResponse) return hookResponse
    const response = new Promise<ElicitResult>(resolve => {
      const onAbort = () => resolve({ action: 'cancel' })
      if (extra.signal.aborted) { onAbort(); return }
      setAppState(prev => ({ ...prev, elicitation: { queue: [...prev.elicitation.queue,
        { serverName, requestId: extra.requestId, params: request.params, signal: extra.signal,
          waitingState,
          respond: (result) => { extra.signal.removeEventListener('abort', onAbort); resolve(result) } }] }}))
      extra.signal.addEventListener('abort', onAbort, { once: true })
    })
    ...
    return runElicitationResultHooks(serverName, rawResult, extra.signal, mode, elicitationId)
  } catch (error) { logMCPError(...); return { action: 'cancel' as const } }   // fail-safe cancel
  // Completion notification (URL mode): flags the matching queue event; dialog reacts
  client.setNotificationHandler(ElicitationCompleteNotificationSchema, notification => {
    setAppState(prev => { /* queue[idx] = { ...queue[idx]!, completed: true } */ })
    if (!found) logMCPDebug(`Ignoring completion notification for unknown elicitation: ...`)
  })
} catch { /* Client wasn't created with elicitation capability - nothing to register */ }
```

**Flow:** server sends elicitation → hooks may answer programmatically (blockingError ⇒ decline) → else enqueue into AppState → UI dialog calls respond() → result hooks can modify/block (blockingError ⇒ decline + notification) → final action returned to server. Abort at any point resolves `{action:'cancel'}` without leaking the listener. The completed flag is set by the SERVER's confirmation notification — matched by (serverName, mode==='url', elicitationId).
**Invariant:** Handler registration failure must be swallowed (capability not declared ≠ crash); unknown elicitationIds in completion notifications are logged and ignored; the error path returns cancel rather than throwing into the SDK.
**Probe:** `grep -n 'ElicitationCompleteNotificationSchema,' src/services/mcp/elicitationHandler.ts | head -1` (`3:` import; usage :175) and `grep -n 'completed: true }' src/services/mcp/elicitationHandler.ts` (`197:`) and `grep -n \"return { action: 'cancel' as const }\" src/services/mcp/elicitationHandler.ts` (`169:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerElicitationHandler", limit: 5 });
```

## Verdict
Adopt hook-first ordering, abort-cancels contract, completion-flag pattern, and capability-guarded registration. Adapt state management to your framework. Omit React dialog components (product surface).
