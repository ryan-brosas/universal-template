<!-- capsule-v2 -->
# agent-loop-tool-call-suspension

## Source
- Repo: `mastra`
- Path: `packages/core/src/loop/workflows/agentic-execution/tool-call-step.ts`
- Symbol: `toolCallStep.suspend`
- Lines: 1025-1045
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.core.src.loop.workflows.agentic-execution.tool-call-step.suspend`

## Signature & Data Shape
```typescript
interface SuspendedToolCallPayload {
  toolCallId: string;
  toolName: string;
  args: Record<string, unknown>;
  permissionRequest?: {
    title: string;
    options: Array<{ optionId: string; name: string }>;
  };
}
```

## Decisive Source Excerpt
```typescript
if (toolResult?.status === 'suspended') {
  await suspend(
    {
      toolCallId: call.toolCallId,
      toolName: call.toolName,
      args: call.input,
      permissionRequest: toolResult.suspendPayload?.permissionRequest,
      __workflow_meta: {
        path: [call.toolName],
      },
    },
    {
      resumeLabel: toolResult.resumeLabel ?? `resume-${call.toolName}`,
    },
  );
  return { status: 'suspended' };
}
```

## Flow
1. Agent loop executes tools emitted in model response.
2. If a tool returns `{ status: 'suspended' }` (e.g. human approval required), the step halts immediately.
3. Package the suspension metadata with `toolCallId`, tool input arguments, and optional permission request options.
4. Set `__workflow_meta.path` to enable nested path unwrapping upon resumption.
5. Provide a deterministic `resumeLabel` (or inherit tool-specified label).

## Invariant
Tool-call suspension must capture exact invocation arguments alongside the suspended tool ID, and prevent partial execution of subsequent chained tools within the same turn until resumed.

## Direct-Test Probe
- File: `packages/core/src/loop/test-utils/aimock/scenarios/auto-resume-suspended-tools.scenario.test.ts`
- Lines: 155-175
- Suite: `describe('auto-resume-suspended-tools')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"toolCallStep suspend resumeLabel agentic-execution"}'
```

## Verdict
Adopt the tool-call suspension protocol with deterministic resume labels.
