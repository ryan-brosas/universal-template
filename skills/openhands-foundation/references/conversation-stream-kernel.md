<!-- capsule-v2 -->
# Conversation stream kernel — subscribing to an agent event stream without re-receiving preloaded history, and surviving refetch/reconnect races

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How does a client combine a REST history preload with a WebSocket live subscription so nothing is missed, duplicated into side effects, or torn down by background refetches?

## Connected graph-selected seam
**Path/Symbol:** `src/contexts/conversation-websocket-context.tsx:ConversationWebSocketProvider` (lines 121–1214), with `src/hooks/query/use-conversation-history.ts:useConversationHistory` (30–98).
**Signature:** `function ConversationWebSocketProvider({ children, conversationId, conversationUrl, sessionApiKey, subConversations, subConversationIds }): JSX.Element`.
**Data Shape:** Props: optional conversation id/url/session key + planning sub-conversations. Emits context `{ connectionState: "CONNECTING"|"OPEN"|"CLOSING"|"CLOSED", sendMessage: (msg) => Promise<{queued:boolean}>, isLoadingHistory: boolean, reconnect: () => void }`.

### Decisive source
```ts
// Build WebSocket URL from props.
//
// We deliberately wait for the FIRST history load (`isPending`: no data for
// this query key yet) before opening the socket, so the WS subscription can
// use `resend_mode='since'` with a meaningful `after_timestamp` instead of
// falling back to `resend_mode='all'`. The gate is intentionally NOT on
// `isFetching`: background refetches (e.g. the `refetchOnMount` fired when
// returning to a conversation) must never tear a live socket down — on a
// flaky link that caused a refetch → teardown → reconnect → refetch loop
// that kept the conversation stuck at "Connecting" for minutes.
const wsUrl = useMemo(() => {
  if (!conversationId || !conversationUrl) return null;
  if (isPreloadingHistory) return null;
  return buildWebSocketUrl(conversationId, conversationUrl);
}, [conversationId, conversationUrl, isPreloadingHistory]);

const queryParams: Record<string, string | boolean> = initialAfterTimestamp
  ? { resend_mode: "since", after_timestamp: initialAfterTimestamp }
  : { resend_mode: "all" };
```

**Flow:** (1) `useConversationHistory` REST-fetches the newest 50 events (`TIMESTAMP_DESC`, reversed to chronological). (2) While that first load is pending, `wsUrl` is null — no socket exists yet. (3) On data, `initialAfterTimestamp` = latest event timestamp; the socket opens with `resend_mode='since'&after_timestamp=<tail>` (or `'all'` if the page was empty or the load errored). (4) Every WS message passes type guards; deltas are buffered (see `streaming-delta-batcher`), duplicates skip non-idempotent side effects, then error banners / optimistic-echo consumption / cache invalidation / state mirrors run. (5) `sendMessage` sends `{...message, run:true}` over the socket when OPEN; otherwise queues via `ConversationClient.sendEvent(..., {run:true})` and returns `{queued:true}` so the caller skips optimistic UI. (6) A second parallel socket serves the planning sub-conversation with `resend_all:true` and count-based history detection via `EventService.getEventCount`. (7) Conversation switch: a `useLayoutEffect` runs BEFORE seeding effects and calls `clearEventsForConversation(nextId)` (atomic clear + rebind) plus metrics/browser resets.

**Invariant:** The gate must distinguish "never loaded" (`isPending`) from "refetching" (`isFetching`); a background refetch or reconnect replay may duplicate events in the store but must never re-run side effects (deduped by event id) nor drop an open socket. Error taxonomy: connection errors are transient (cleared by any later event/`onOpen`, shown only after a first successful connect); conversation errors (bad API key) stay sticky.

**Probe:** `__tests__/contexts/conversation-websocket-context.test.tsx` — fixtures `renderProvider`/`deliver`/`makeStreamingDelta`/`makeAgentReply` pin echo consumption, delta handling, and history-page behavior. RUNNER BLOCK: vitest not executable here (no node_modules in either clean read-only inspo checkout); decisive ranges were read directly instead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "ConversationWebSocketProvider resend_mode since history gate", limit: 8 });
// executed this pass -> ConversationWebSocketProvider src/contexts/conversation-websocket-context.tsx 121-1214,
// useConversationHistory src/hooks/query/use-conversation-history.ts 30-98 (has_more: true)
```

## Verdict
Adopt the preload-then-`since`-subscribe lifecycle, `isPending`-only gating, queued-send fallback contract `{queued}`, and the layout-effect ordering for store clears. Adapt the TanStack Query/zustand wiring and the typescript-client calls to your host. Omit OpenHands-specific planning sub-conversations and cloud provisioning semantics. Coverage: both files report `no_recorded_issue` from check_index_coverage; direct test execution blocked as recorded above.
