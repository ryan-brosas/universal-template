<!-- capsule-v2 -->
# thread-adapter-promise-boundary

## Source
- Repo: `copilotkit`
- Path: `packages/channels-core/src/thread-promise-contract.test.ts`
- Symbol: `Thread.delete`
- Lines: 10-45
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-core.src.thread.Thread.delete`

## Signature & Data Shape
```typescript
interface ThreadAdapter {
  delete(target: { id: string }): Promise<void> | void;
}

export class Thread {
  delete(target: { id: string }): Promise<void>;
}
```

## Decisive Source Excerpt
```typescript
function setupThreadWithSyncDeleteFailure(failure: Error): Thread {
  const adapter = new FakeAdapter();
  adapter.delete = () => {
    throw failure;
  };
  const deps: ThreadDeps = {
    adapter,
    replyTarget: {},
    conversationKey: "thread-promise-contract",
    channelName: "test",
    threadId: "thread-promise-contract",
    registry: new ActionRegistry({ store: new InMemoryActionStore() }),
    agentFactory: (threadId) => {
      throw new Error(`agentFactory not needed in this test: ${threadId}`);
    },
    tools: new Map(),
    toolDescriptors: [],
    context: [],
    registerWaiter: () => undefined,
    interruptHandlers: new Map(),
    state: new MemoryStore(),
    user: null,
    actor: { id: "actor", kind: "unknown" },
  };
  return new Thread(deps);
}

test("a synchronous non-managed adapter failure returns a rejected Promise", async () => {
  const failure = new Error("adapter delete failed synchronously");
  const thread = setupThreadWithSyncDeleteFailure(failure);
  let deletion: Promise<void> | undefined;

  expect(() => {
    deletion = thread.delete({ id: "message-1" });
  }).not.toThrow();
  await expect(deletion).rejects.toBe(failure);
});
```

## Flow
1. Caller executes high-level thread methods (e.g. `thread.delete(...)`).
2. High-level thread wrapper delegates operation to the platform-specific adapter within an async function or Promise constructor boundary.
3. If the underlying adapter method throws synchronously, the error is converted into an asynchronous Promise rejection.
4. Callers are guaranteed that method calls never throw synchronously from the dispatch frame.

## Invariant
All thread mutation operations must convert synchronous adapter exceptions into rejected Promises, preventing unhandled synchronous crashes in async dispatch pipelines.

## Direct-Test Probe
- File: `packages/channels-core/src/thread-promise-contract.test.ts`
- Lines: 36-45
- Assertion: `expect(() => { thread.delete(...) }).not.toThrow()` and `await expect(deletion).rejects.toBe(failure)`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"thread-promise-contract setupThreadWithSyncDeleteFailure"}'
```

## Verdict
Adopt the promise boundary contract for all channel thread and message mutation methods.
