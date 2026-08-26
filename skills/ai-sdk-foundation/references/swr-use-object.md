<!-- capsule-v2 -->
# SWR-keyed useObject — how does a streaming-JSON hook dedupe renders and validate only at stream close?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do partial objects reach React cheaply during streaming, and where does schema validation actually run?

## useObject
**Path/Symbol:** `packages/react/src/use-object.ts:useObject` (:120-266).
**Signature:** `useObject({api, schema, id?, initialValue?, fetch?, onFinish?, onError?, headers?: Resolvable, credentials?}): {submit, object, error, isLoading, stop, clear}`.
**Data Shape:** state lives in SWR under key `[completionId, 'object']` (completionId = explicit id ?? React `useId()`) so multiple components sharing an id share the object; `object` is `DeepPartial<RESULT> | undefined`.

### Decisive source
```ts
await response.body.pipeThrough(new TextDecoderStream()).pipeTo(
  new WritableStream<string>({
    async write(chunk) {
      accumulatedText += chunk;
      const { value } = await parsePartialJson(accumulatedText);
      if (!isDeepEqualData(latestObject, value)) { latestObject = value; mutate(value); } // deep-equal gate BEFORE mutate
    },
    async close() { // validation happens at CLOSE, not per chunk
      setIsLoading(false); abortControllerRef.current = null;
      if (onFinish != null) {
        const validationResult = await safeValidateTypes({ value: latestObject, schema: asSchema(schema) });
        onFinish(validationResult.success ? {object: validationResult.value, error: undefined}
                                         : {object: undefined,   error: validationResult.error});
      }
    },
  }));
// aborts are swallowed — stop() is not an error:
catch (error) { if (isAbortError(error)) return; /* ... */ }
```

**Flow:** submit clears previous state → isLoading true → fresh AbortController tracked in ref → headers resolved via `await resolve(headers)` (async token refresh supported) → POST JSON body → !ok throws response TEXT; empty body throws → every text chunk: append + parsePartialJson + deep-equal gate + `mutate` (SWR) → close: safe-validate against the FULL schema and deliver `{object}` or `{object: undefined, error}` to onFinish → any thrown error lands in catch: AbortError returns silently; others call onError + set error state. `stop()` aborts but KEEPS the partial object; `clear()` stops AND wipes.
**Invariant:** the deep-equal gate (`isDeepEqualData`) is load-bearing — without it every whitespace delta re-renders consumers. Validation NEVER runs mid-stream (partials are structurally invalid by definition); it runs exactly once at close, and a failed validation still fires onFinish with `error` rather than throwing. The same kernel trio (`parsePartialJson` + `isDeepEqualData` + asSchema validation) is reused by `useStableValue` (`packages/react/src/util/use-stable-value.ts:8-18`, effect-gated variant).
**Probe:** `packages/react/src/use-object.ui.test.tsx:90/:101/:109` (stream render / no-error / isLoading lifecycle).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "useObject parsePartialJson isDeepEqualData mutate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt SWR-style keyed shared state, the write-path deep-equal gate, and close-boundary validation. Adapt transport/error surface to your API shape. Omit the legacy completion-API path (`packages/ai/src/ui/call-completion-api.ts` — superseded product surface kept for back-compat).
