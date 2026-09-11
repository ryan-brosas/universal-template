<!-- capsule-v2 -->
# observational-memory-workflow-kernel

## Source
- Repo: `mastra`
- Path: `packages/memory/src/processors/observational-memory/__tests__/processor-workflow-circular.test.ts`
- Symbol: `describe('processor workflow + observational memory')`
- Lines: 95-170
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.memory.src.processors.observational-memory.__tests__.processor-workflow-circular.test.createGuardrailWorkflow`

## Signature & Data Shape
```typescript
interface ObservationalMemoryOptions {
  enabled: boolean;
  observation: {
    model: MastraLanguageModel;
    messageTokens: number;
    bufferTokens: boolean;
  };
  reflection: {
    observationTokens: number;
  };
}
```

## Decisive Source Excerpt
```typescript
function createGuardrailWorkflow(): InputProcessorOrWorkflow {
  return createWorkflow({
    id: 'input-guardrails',
    inputSchema: ProcessorStepSchema,
    outputSchema: ProcessorStepSchema,
  })
    .then(createStep({ id: 'guard', processInput: async ({ messages }) => messages }))
    .commit() as unknown as InputProcessorOrWorkflow;
}

// Make the workflows store serialize the snapshot the way a standard SQL adapter (e.g. pg) does:
// a plain JSON.stringify with no circular-safe replacer. libsql's safeStringify hides the bug by
// silently rewriting cycles to "[Circular]" — that lossy behaviour is exactly what we must NOT
// rely on. Capture every snapshot so the test can prove they round-trip losslessly. If a snapshot
// is unserializable, report which top-level field still holds the cycle.
async function captureSnapshotSerialization(storage: InMemoryStore) {
  const captured: string[] = [];
  const workflowsStore: any = await storage.getStore('workflows');
  const original = workflowsStore.persistWorkflowSnapshot.bind(workflowsStore);
  vi.spyOn(workflowsStore, 'persistWorkflowSnapshot').mockImplementation(async (args: any) => {
    try {
      captured.push(JSON.stringify(args.snapshot));
    } catch (error) {
      throw new Error(`Circular reference in snapshot: ${error}`);
    }
    return original(args);
  });
  return captured;
}
```

## Flow
1. Configure `Memory` with `observationalMemory` enabled, binding observer and reflector token thresholds.
2. Compose input guardrails as a `ProcessorWorkflow` executed before agent turns.
3. Track observation turns with serializable projections (`ObservationTurn.toJSON()`).
4. Persist workflow snapshots through standard storage adapters using strict, cycle-free `JSON.stringify`.
5. Ensure snapshots round-trip without relying on lossy `[Circular]` string rewriting.

## Invariant
Observational memory turn records embedded in workflow state snapshots must be strictly cycle-free (`toJSON` projection), guaranteeing lossless JSON serialization across SQL/PostgreSQL/LibSQL storage drivers.

## Direct-Test Probe
- File: `packages/memory/src/processors/observational-memory/__tests__/processor-workflow-circular.test.ts`
- Lines: 122-170
- Assertion: lossless `JSON.stringify(args.snapshot)` without cycle detection exceptions

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"observational-memory processor-workflow-circular ObservationTurn"}'
```

## Verdict
Adopt the cycle-free observational memory snapshot projection and processor workflow integration.
