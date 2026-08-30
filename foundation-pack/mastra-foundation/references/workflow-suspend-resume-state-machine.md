<!-- capsule-v2 -->
# workflow-suspend-resume-state-machine

## Source
- Repo: `mastra`
- Path: `packages/core/src/workflows/workflow.ts`
- Symbol: `Run._resume`
- Lines: 4362-4480
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.core.src.workflows.workflow.Run._resume`

## Signature & Data Shape
```typescript
protected async _resume<TResume>(
  params: {
    resumeData?: TResume;
    step?: Step<string, any, any, TResume, any, any, TEngineType, any> | string | string[];
    label?: string;
    requestContext?: RequestContext<TRequestContext>;
    retryCount?: number;
    tracingOptions?: TracingOptions;
    outputWriter?: OutputWriter;
    format?: 'legacy' | 'vnext' | undefined;
    isVNext?: boolean;
    outputOptions?: {
      includeState?: boolean;
      includeResumeLabels?: boolean;
    };
    forEachIndex?: number;
    perStep?: boolean;
    actor?: ActorSignal;
  } & Partial<ObservabilityContext>,
): Promise<WorkflowResult<TState, TInput, TOutput, TSteps>>;
```

## Decisive Source Excerpt
```typescript
const workflowsStore = await this.#mastra?.getStorage()?.getStore('workflows');
const snapshot = await workflowsStore?.loadWorkflowSnapshot({
  workflowName: this.workflowId,
  runId: this.runId,
});

if (!snapshot) {
  throw new Error('No snapshot found for this workflow run: ' + this.workflowId + ' ' + this.runId);
}

if (snapshot.status !== 'suspended') {
  throw new Error('This workflow run was not suspended');
}

const snapshotResumeLabel = params.label ? snapshot?.resumeLabels?.[params.label] : undefined;
const stepParam = snapshotResumeLabel?.stepId ?? params.step;

// Auto-detect suspended steps if no step is provided
let steps: string[];
if (stepParam) {
  let newStepParam = stepParam;
  if (typeof stepParam === 'string') {
    newStepParam = stepParam.split('.');
  }
  steps = (Array.isArray(newStepParam) ? newStepParam : [newStepParam]).map(step =>
    typeof step === 'string' ? step : step?.id,
  );
} else {
  // Use suspendedPaths to detect suspended steps
  const suspendedStepPaths: string[][] = [];

  Object.entries(snapshot?.suspendedPaths ?? {}).forEach(([stepId, _executionPath]) => {
    const stepResult = snapshot?.context?.[stepId];
    if (stepResult && typeof stepResult === 'object' && 'status' in stepResult) {
      const stepRes = stepResult as any;
      if (stepRes.status === 'suspended') {
        const nestedPath = stepRes.suspendPayload?.__workflow_meta?.path;
        if (nestedPath && Array.isArray(nestedPath)) {
          suspendedStepPaths.push([stepId, ...nestedPath]);
        } else {
          suspendedStepPaths.push([stepId]);
        }
      }
    }
  });

  if (suspendedStepPaths.length === 0) {
    throw new Error('No suspended steps found in this workflow run');
  }

  if (suspendedStepPaths.length === 1) {
    steps = suspendedStepPaths[0]!;
  } else {
    const pathStrings = suspendedStepPaths.map(path => `[${path.join(', ')}]`);
    throw new Error(
      `Multiple suspended steps found: ${pathStrings.join(', ')}. ` +
        'Please specify which step to resume using the "step" parameter.',
    );
  }
}
```

## Flow
1. Load workflow snapshot from persistent storage via `workflowsStore.loadWorkflowSnapshot({ workflowName, runId })`; throw if snapshot is missing.
2. Assert `snapshot.status === 'suspended'`; fail loudly if the run is not in suspended status.
3. Resolve target step: if `params.label` is provided, look up `snapshot.resumeLabels[label].stepId`.
4. If no explicit step or label was given, scan `snapshot.suspendedPaths` and unwrapped `__workflow_meta.path` entries.
5. If exactly one suspended step path is discovered, auto-target it; if multiple suspended steps exist, throw an explicit disambiguation error requiring the caller to specify the step parameter.

## Invariant
A workflow resume must never guess when multiple concurrent branches are suspended. When auto-detection encounters `suspendedStepPaths.length > 1`, it must fail closed with an explicit list of available paths, and snapshot loading must reject any non-suspended state before touching step state.

## Direct-Test Probe
- File: `packages/core/src/workflows/nested-resume-label.test.ts`
- Lines: 20-65
- Suite: `describe('resume-label propagation')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"Run._resume loadWorkflowSnapshot suspendedPaths"}'
```

## Verdict
Adopt the snapshot-based suspend/resume state machine, label-to-step resolution, and unambiguous multi-step auto-detection ladder.
