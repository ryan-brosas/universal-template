<!-- capsule-v2 -->
# generateObject non-stream twin — how do you validate a COMPLETE structured response once, with repair, and fail with full response context?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the exact parse→validate→repair ladder for a finished (non-streamed) JSON answer, and which failure carries which context?

## Repair-gated final validation
**Path/Symbol:** `packages/ai/src/generate-object/parse-and-validate-object-result.ts:parseAndValidateObjectResultWithRepair` (:77–111); inner `parseAndValidateObjectResult` (:21–64).
**Signature:** `(result: string, outputStrategy: OutputStrategy<any, RESULT, any>, repairText: RepairTextFunction | undefined, context: {response, usage, finishReason}): Promise<RESULT>`.
**Data Shape:** Success → validated RESULT. Every failure throws `NoObjectGeneratedError` whose `cause` distinguishes the two failure classes (`JSONParseError` vs schema `TypeValidationError`) and whose body carries text + response + usage + finishReason. Repair engages ONLY when cause is exactly one of those two types.

### Decisive source
```ts
try {
  return await parseAndValidateObjectResult(result, outputStrategy, context);
} catch (error) {
  if (
    repairText != null &&
    NoObjectGeneratedError.isInstance(error) &&
    (JSONParseError.isInstance(error.cause) ||
     TypeValidationError.isInstance(error.cause))
  ) {
    const repairedText = await repairText({ text: result, error: error.cause });
    if (repairedText === null) throw error;        // null = "cannot repair" → ORIGINAL error
    return await parseAndValidateObjectResult(repairedText, outputStrategy, context);
  }
  throw error;
}
// inner: safeParseJSON → NoObjectGeneratedError('could not parse') on parse fail;
//        outputStrategy.validateFinalResult(value, {text, response, usage})
//        → NoObjectGeneratedError('did not match schema') on validation fail.
```

**Flow:** generate-object.ts awaits the single `doGenerate` (responseFormat `{type:'json', schema, name, description}` :400–405), extracts text via `extractTextContent(generateResult.content)` — ABSENT text throws `NoObjectGeneratedError` 'the model did not return a response' BEFORE any parsing (:427–433) — then runs this ladder, notifies onFinish with the object, wraps ALL errors through `wrapGatewayError` in the outer catch (:496–500). Stream side reuses the SAME function at finish time (stream-object.ts :787–801) — one contract, two transports. Input validation ladder (validate-object-generation-input.ts :4–144): no-schema forbids ALL schema params; object/array REQUIRE schema and forbid enumValues; enum requires strings-only enumValues and forbids schema/name/description — fail-fast `InvalidArgumentError`s before any model call.
**Invariant:** Exactly ONE repair attempt; repair returning `null` re-throws the ORIGINAL error (not a new one), so consumers branch on stable error identity. The repaired pass goes through the identical parse+validate (a repair that fixes JSON but breaks the schema fails again — no second repair). Note the asymmetry vs the tool-call repair hook (tool-calls.md): there repair is keyed to tool errors; here to whole-response JSON/schema errors.
**Probe:** `packages/ai/src/generate-object/stream-object.test.ts` repair block :1464 (repairs JSONParseError), :1507 (repairs TypeValidationError — proving schema failures are also repair-eligible), :1552 (null repair rethrows original), :1597 (markdown-fenced JSON repair), :1647 (unrepairable → NoObjectGeneratedError); `packages/ai/src/generate-object/generate-object.test.ts` mirrors for non-stream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "parseAndValidateObjectResultWithRepair repairText NoObjectGeneratedError", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the typed-cause repair gate, single-attempt + null-rethrow semantics, and the context-stuffed error body verbatim; adapt the error taxonomy names to host; omit the telemetry/onFinish notification plumbing if your host has its own event bus. Coverage caveat: index best-effort; excerpts read directly at HEAD.
