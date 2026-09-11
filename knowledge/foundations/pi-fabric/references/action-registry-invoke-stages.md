<!-- capsule-v2 -->
# Registry invoke stage machine — how does one nested tool call move through guard → prepare → validate → approve → invoke with audit and trace intact?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the ordering contract for executing a `provider.action` call inside a fabric_exec run?

## Connected graph-selected seam
**Path/Symbol:** `src/core/action-registry.ts` — `ActionRegistry.invoke` (:461-625), `#parseRef` (:645-655), `previewArgs` (:122-137), `boundedResult` (:171-199), `failedResultError/Outcome` (:156-169), `NESTED_TOOL_CALL_ID_PREFIX` (:92).
**Signature:** `invoke(ref, args, context)` where context carries `authorize?`, `approve`, `audits[]`, `maxResultChars`, `trace?`, `observeInvocation?`; failure stage is tracked as `"resolve" | "guard" | "prepare" | "validate" | "approve" | "invoke"` for trace attribution.
**Data Shape:** ref grammar `provider.action` (FIRST dot splits; empty halves rejected); nested ids `${FABRIC_NESTED_TOOL_CALL_ID_PREFIX}${uuid}` — extensions detect nested-vs-top-level calls by prefix, never by id shape; bounded result envelope `{ fabricTruncated: true, originalChars, preview }`.

### Decisive source
```ts
      failureStage = "validate";
      const invalid = validationMessage(action.inputSchema, preparedArgs);
      if (invalid) throw new Error(`Invalid arguments for ${ref}: ${invalid}`);

      failureStage = "approve";
      await runAbortable(context.signal, () => context.approve(action, preparedArgs));

      failureStage = "invoke";
      const nestedToolCallId = `${NESTED_TOOL_CALL_ID_PREFIX}${randomUUID()}`;
```

**Flow:** resolve descriptor (abortable) → authorize (guard) → provider.prepareArguments (optional hook; non-object return = loud throw) → schema-validate PREPARED args via typebox (`Value.Check`, first 5 error messages joined, validator crash = "Schema validator failed" not a pass) → approve → mint nestedToolCallId → push live audit + emit `call_start` → invoke with wrapped callbacks (update/activity/attachMedia/updateArguments/attachPreview all no-op once `invocationActive` flips — late async callbacks can't mutate a finished audit) → proxy through optional toolResultProxy → `boundedResult` enforces maxResultChars on the SERIALIZED form while returning the ORIGINAL object when it fits → failed-status results (failed/stopped/timed_out) are surfaced as failed nested calls WITHOUT hiding the payload → `call_end` + traceOperation succeed/fail. Catch path attributes the failure to the CURRENT failureStage; finally flips `invocationActive` off and stamps `endedAt ??=`.
**Invariant:** validation happens BEFORE approval so hostile args are never shown to an approver, and approval BEFORE execution; every call gets exactly one audit entry with bounded previews (2k arg chars, 16k write-content exception, 32 keys, 64k retained value) that never shrinks the model-visible result itself; bare action names (no dot) resolve only through a UNIQUE-name walk across providers with an explicit ambiguity error listing qualifying refs.
**Probe:** `tests/action-registry.test.ts:356` ("validates arguments before approval or execution"), `:278` ("marks failed agent results as failed nested calls without hiding the result"), `:318` ("bounds retained audit previews without shrinking provider results"), `:84` ("describes a bare action name through the unique-name fallback").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ActionRegistry invoke prepareArguments validate approve nestedToolCallId audit", limit: 5, fields: ["signature", "name", "file"] });
```
