<!-- capsule-v2 -->
# agent-tool-memory-isolation

## Source
- Repo: `mastra`
- Path: `packages/core/src/agent/__tests__/workflow-tool-memory-isolation.test.ts`
- Symbol: `describe('Workflow tool MastraMemory isolation')`
- Lines: 73-142
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.core.src.agent.__tests__.workflow-tool-memory-isolation.test.execute`

## Signature & Data Shape
```typescript
interface RequestContextMemoryPayload {
  thread?: { id: string };
  resource?: string;
  [key: string]: unknown;
}
```

## Decisive Source Excerpt
```typescript
const parentThreadId = randomUUID();
const subAgentThreadId = randomUUID();
const resourceId = 'test-user';
const mockMemory = new MockMemory();

await mockMemory.createThread({ threadId: parentThreadId, resourceId });
await mockMemory.createThread({ threadId: subAgentThreadId, resourceId });

const subAgent = new Agent({
  id: 'sub-agent',
  name: 'Sub Agent',
  instructions: 'You are a sub-agent.',
  model: createSimpleTextModel(),
  memory: mockMemory,
});

// This step runs a sub-agent with its OWN thread, which overwrites
// MastraMemory on the shared requestContext.
const subAgentStep = createStep({
  id: 'sub-agent-step',
  inputSchema: z.object({ prompt: z.string() }),
  outputSchema: z.object({ text: z.string() }),
  execute: async ({ inputData, requestContext }) => {
    const stream = await subAgent.stream(inputData.prompt, {
      memory: { thread: subAgentThreadId, resource: resourceId },
      requestContext,
      maxSteps: 1,
    });
    await stream.consumeStream();
    return { text: await stream.text };
  },
});

const parentAgent = new Agent({
  id: 'parent-agent',
  name: 'Parent Agent',
  instructions: 'You are a parent agent.',
  model: createWorkflowCallingModel('workflow-myWorkflow'),
  memory: mockMemory,
  workflows: { myWorkflow },
});

new Mastra({ agents: { parentAgent }, logger: false });
const requestContext = new RequestContext();

const stream = await parentAgent.stream('Do something', {
  memory: { thread: parentThreadId, resource: resourceId },
  requestContext,
  maxSteps: 5,
});
await stream.consumeStream();

// After the workflow tool finishes, MastraMemory must point back
// to the parent's thread — not the sub-agent's thread.
const restoredMemory = requestContext.get('MastraMemory') as any;
expect(restoredMemory).toBeDefined();
expect(restoredMemory?.thread?.id).toBe(parentThreadId);
```

## Flow
1. Parent agent receives a turn request on a specified `parentThreadId`.
2. Agent initiates a tool call invoking a sub-agent workflow.
3. Sub-agent assigns its own `subAgentThreadId` to `MastraMemory` on `requestContext`.
4. Tool wrapper executes sub-agent within a scoped try/finally bracket.
5. In the finally block, the tool wrapper restores the original `parentThreadId` reference onto `requestContext`, even if the sub-agent threw an unhandled exception.

## Invariant
Sub-agent tool execution within a nested workflow must never pollute or permanently rebind the parent conversation thread. The parent's memory context must be restored unconditionally in `finally` upon tool return.

## Direct-Test Probe
- File: `packages/core/src/agent/__tests__/workflow-tool-memory-isolation.test.ts`
- Lines: 73-142
- Assertion: `expect(restoredMemory?.thread?.id).toBe(parentThreadId)`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"workflow-tool-memory-isolation restoredMemory MastraMemory"}'
```

## Verdict
Adopt the request-context memory isolation bracket for multi-agent hierarchical invocations.
