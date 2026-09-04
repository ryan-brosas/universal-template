<!-- capsule-v2 -->
# agent-run-loop-subscriber-proxy

## Source
- Repo: `copilotkit`
- Path: `packages/channels-core/src/run-loop.ts`
- Symbol: `mergeAgentSubscribers` / `invokeSubscriberPair`
- Lines: 98-220
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-core.src.run-loop.mergeAgentSubscribers`

## Signature & Data Shape
```typescript
export function mergeAgentSubscribers(
  first: AgentSubscriber,
  second: AgentSubscriber,
  options?: SubscriberFanoutOptions,
): AgentSubscriber;

interface SubscriberFanoutOptions {
  canonicalRun?: CanonicalRunIdentity;
  onInnerRunError?: (event: RunErrorEvent) => void;
  onRendererError?: (error: unknown) => void;
  isRendererClosed?: () => boolean;
}
```

## Decisive Source Excerpt
```typescript
async function invokeSubscriberPair(
  rendererCallback: SubscriberCallback | undefined,
  ingestionCallback: SubscriberCallback | undefined,
  params: unknown,
  onRendererError?: (error: unknown) => void,
  isRendererClosed?: () => boolean,
): Promise<unknown> {
  let rendererResult: unknown;
  let ingestionResult: unknown;
  let rendererError: unknown;
  let ingestionError: unknown;
  let rendererFailed = false;
  let ingestionFailed = false;

  try {
    ingestionResult = await ingestionCallback?.(params);
  } catch (error) {
    ingestionFailed = true;
    ingestionError = error;
  }
  if (!isRendererClosed?.()) {
    try {
      rendererResult = await rendererCallback?.(params);
    } catch (error) {
      rendererFailed = true;
      rendererError = error;
    }
  }

  if (ingestionFailed) throw ingestionError;
  if (rendererFailed) {
    if (!onRendererError) throw rendererError;
    onRendererError(rendererError);
  }
  return mergeSubscriberResults(rendererResult, ingestionResult);
}

export function mergeAgentSubscribers(
  first: AgentSubscriber,
  second: AgentSubscriber,
  options: SubscriberFanoutOptions = {},
): AgentSubscriber {
  const stampedEvents = new WeakMap<BaseEvent, BaseEvent>();
  return new Proxy({} as AgentSubscriber, {
    get(_target, property: keyof AgentSubscriber) {
      const firstCallback = first[property];
      const secondCallback = second[property];
      if (
        typeof firstCallback !== "function" &&
        typeof secondCallback !== "function"
      ) {
        return undefined;
      }

      return async (params: unknown) => {
        const canonicalParams = canonicalizeSubscriberParams(
          params,
          options,
          stampedEvents,
        );
        if (canonicalParams === undefined) return undefined;
        return invokeSubscriberPair(
          typeof firstCallback === "function"
            ? (firstCallback as SubscriberCallback)
            : undefined,
          typeof secondCallback === "function"
            ? (secondCallback as SubscriberCallback)
            : undefined,
          canonicalParams,
          options.onRendererError,
          options.isRendererClosed,
        );
      };
    },
  });
}
```

## Flow
1. Wrap two subscriber instances in a dynamic `Proxy` that traps all method property reads.
2. Intercept dispatched events and stamp canonical `threadId` and `runId` using `WeakMap` memoization to prevent object mutation.
3. In `invokeSubscriberPair`, invoke the canonical ingestion callback first in a separate try/catch.
4. If the renderer is not closed (`!isRendererClosed()`), invoke the renderer callback.
5. Ingestion failures throw immediately; renderer failures are routed to `onRendererError` without corrupting ingestion state.

## Invariant
A channel renderer failure must never suppress or block the canonical agent runner from receiving turn events. Ingestion runs before rendering, and renderer exceptions route to non-fatal error traps rather than crashing the run loop.

## Direct-Test Probe
- File: `packages/channels-core/src/canonical-run-loop.test.ts`
- Lines: 20-85
- Suite: `test("canonical run loop merges and isolates subscriber failures")`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"mergeAgentSubscribers invokeSubscriberPair canonicalRun"}'
```

## Verdict
Adopt the dynamic Proxy subscriber fanout and isolated pair execution boundary for multi-channel agent runners.
