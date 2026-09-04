<!-- capsule-v2 -->
# Call-options validation gate — which model call options are validated eagerly, and what shape does the normalized object keep?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Where is the boundary that turns bad user call options (`maxOutputTokens: 0`, string temperature) into typed argument errors BEFORE a provider request, and why do only some fields get checks?

## prepareLanguageModelCallOptions
**Path/Symbol:** `packages/ai/src/prompt/prepare-language-model-call-options.ts:prepareLanguageModelCallOptions` (:7-107).
**Signature:** `(options: LanguageModelCallOptions): LanguageModelCallOptions` — same keys in/out; throws `InvalidArgumentError({parameter, value, message})`.
**Data Shape:** Validated fields: `maxOutputTokens` (Number.isInteger AND >= 1), `temperature` (typeof number), `topP` (number), `topK` (number), `presencePenalty` (number), `frequencyPenalty` (number), `seed` (integer). Pass-through with NO type check: `stopSequences`, `reasoning`.

### Decisive source
```ts
if (maxOutputTokens != null) {
  if (!Number.isInteger(maxOutputTokens)) throw new InvalidArgumentError({
    parameter: 'maxOutputTokens', value: maxOutputTokens,
    message: 'maxOutputTokens must be an integer' });
  if (maxOutputTokens < 1) throw new InvalidArgumentError({
    parameter: 'maxOutputTokens', value: maxOutputTokens,
    message: 'maxOutputTokens must be >= 1' });
}
// ... typeof-number gates for temperature/topP/topK/presencePenalty/frequencyPenalty ...
if (seed != null && !Number.isInteger(seed)) { /* InvalidArgumentError */ }
return { maxOutputTokens, temperature, topP, topK, presencePenalty,
         frequencyPenalty, stopSequences, seed, reasoning };
```

**Flow:** every check is gated on `!= null` first — `undefined`/`null` options are VALID and mean "provider default"; present-but-wrong types throw synchronously at prompt-assembly time, never inside the provider HTTP layer.
**Invariant:** The validator is the SINGLE eager boundary: providers can assume integer ≥1 maxOutputTokens and numeric sampling params without re-checking. Two distinct failure classes for maxOutputTokens (non-integer vs <1) exist because `0.5` and `0` fail for different reasons (schema vs range) — merging them loses the actionable message. Unvalidated fields are pass-through by design: adding checks there would reject provider-specific shapes.
**Probe:** `packages/ai/src/prompt/prepare-language-model-call-options.test.ts` (:299-line suite pinning each field's error message and the null-pass-through behavior — e.g. non-integer maxOutputTokens, zero rejection, undefined temperature accepted).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"prepareLanguageModelCallOptions InvalidArgumentError maxOutputTokens","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the null-gated eager validation with per-field messages and the two-class integer/range split; adapt the error type to your hierarchy; omit checks for host-specific option fields exactly as this code omits them for stopSequences/reasoning. Direct-test-pinned via the dedicated suite at this HEAD.
