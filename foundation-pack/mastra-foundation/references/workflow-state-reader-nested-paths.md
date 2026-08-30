<!-- capsule-v2 -->
# workflow-state-reader-nested-paths

## Source
- Repo: `mastra`
- Path: `packages/core/src/workflows/state-reader.ts`
- Symbol: `getWorkflowSuspendedSteps` / `createWorkflowStateReader`
- Lines: 31-105
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.core.src.workflows.state-reader.getWorkflowSuspendedSteps`

## Signature & Data Shape
```typescript
export type WorkflowSuspendedStep = {
  stepId: string;
  path: string[];
  executionPath?: number[];
  step?: WorkflowStateStepResult;
  payload?: any;
  suspendPayload?: any;
  suspendOutput?: any;
  resumeLabels: Record<string, WorkflowResumeLabel>;
};

export function getWorkflowSuspendedSteps(state: WorkflowState): WorkflowSuspendedStep[];
export function createWorkflowStateReader(state: WorkflowState): WorkflowStateReader;
```

## Decisive Source Excerpt
```typescript
const getFirstStepResult = (step?: WorkflowStateStepResult): WorkflowStateSingleStepResult | undefined => {
  return Array.isArray(step) ? (step.find(result => result?.status === 'suspended') ?? step[0]) : step;
};

const getNestedSuspendPath = (step?: WorkflowStateStepResult): string[] => {
  const path = getFirstStepResult(step)?.suspendPayload?.__workflow_meta?.path;
  return Array.isArray(path) ? path.filter((part): part is string => typeof part === 'string') : [];
};

export function getWorkflowSuspendedSteps(state: WorkflowState): WorkflowSuspendedStep[] {
  return Object.entries(state.suspendedPaths ?? {}).map(([stepId, executionPath]) => {
    const step = getStep(state, stepId);
    const firstStepResult = getFirstStepResult(step);
    const nestedPath = getNestedSuspendPath(step);
    const path = nestedPath.length > 0 ? (nestedPath[0] === stepId ? nestedPath : [stepId, ...nestedPath]) : [stepId];
    const resumeLabels = Object.entries(state.resumeLabels ?? {}).reduce(
      (labels, [label, value]) => {
        if (value.stepId === stepId) {
          labels[label] = { ...value };
        }
        return labels;
      },
      {} as Record<string, WorkflowResumeLabel>,
    );

    return {
      stepId,
      path,
      executionPath,
      step,
      payload: Array.isArray(step) ? step.map(result => result?.payload) : step?.payload,
      suspendPayload: firstStepResult?.suspendPayload,
      suspendOutput: firstStepResult?.suspendOutput,
      resumeLabels,
    };
  });
}
```

## Flow
1. Iterate over all entries in `state.suspendedPaths`.
2. Inspect the step result: if it is an array of iterations (e.g. `forEach`), locate the element whose status is `'suspended'`.
3. Extract `__workflow_meta.path` from `suspendPayload` to detect nested sub-workflow suspensions.
4. Construct the canonical composite path: prepend the parent `stepId` if it is not already root of `nestedPath`.
5. Filter and clone only the `resumeLabels` that belong to this particular `stepId`.

## Invariant
Nested sub-workflow paths must preserve hierarchical step identity across depth boundaries. Array step results must select the active suspended branch rather than defaulting to index 0, preventing misdirected resume signals.

## Direct-Test Probe
- File: `packages/core/src/workflows/state-reader.test.ts`
- Lines: 160-195
- Suite: `describe('state-reader nested suspend paths')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"getWorkflowSuspendedSteps getNestedSuspendPath state-reader"}'
```

## Verdict
Adopt the state-reader read model and nested suspend path normalizer for introspecting workflow snapshot states.
