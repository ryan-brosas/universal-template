<!-- capsule-v2 -->
# workflow-step-execution-dag

## Source
- Repo: `mastra`
- Path: `packages/core/src/workflows/workflow.ts`
- Symbol: `Workflow.execute` / `#getInMemoryRunAsWorkflowState`
- Lines: 2688-2780
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.core.src.workflows.workflow.Workflow.execute`

## Signature & Data Shape
```typescript
public async execute(
  params?: {
    inputData?: TInput;
    requestContext?: RequestContext<TRequestContext>;
    tracingOptions?: TracingOptions;
    outputWriter?: OutputWriter;
    format?: 'legacy' | 'vnext' | undefined;
    isVNext?: boolean;
    outputOptions?: {
      includeState?: boolean;
      includeResumeLabels?: boolean;
    };
    actor?: ActorSignal;
  } & Partial<ObservabilityContext>,
): Promise<WorkflowResult<TState, TInput, TOutput, TSteps>>;
```

## Decisive Source Excerpt
```typescript
const run = await this.createRun({
  requestContext: params?.requestContext,
  tracingOptions: params?.tracingOptions,
  outputWriter: params?.outputWriter,
  format: params?.format,
  isVNext: params?.isVNext,
  outputOptions: params?.outputOptions,
  actor: params?.actor,
});

return await run.start({
  inputData: params?.inputData,
  requestContext: params?.requestContext,
  tracingOptions: params?.tracingOptions,
  outputWriter: params?.outputWriter,
  format: params?.format,
  isVNext: params?.isVNext,
  outputOptions: params?.outputOptions,
  actor: params?.actor,
});
```

## Flow
1. Construct an ephemeral or durable `Run` instance bound to the workflow configuration.
2. Initialize execution context, tracing spans, and request context.
3. Traverse the step dependency graph in topological order.
4. Concurrently execute ready parallel branches while preserving input-data immutability.
5. Aggregate final outputs into a structured `WorkflowResult` with terminal status (`'success'`, `'suspended'`, or `'failed'`).

## Invariant
Workflows must maintain idempotent run isolation: starting or executing a workflow creates a dedicated run boundary so that in-flight mutations to state or memory do not leak across concurrent runs of the same workflow definition.

## Direct-Test Probe
- File: `packages/core/src/workflows/workflow.test.ts`
- Lines: 45-120
- Suite: `describe('Workflow execution DAG')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"Workflow.execute createRun run.start"}'
```

## Verdict
Adopt the Workflow DAG builder and run isolation boundaries.
