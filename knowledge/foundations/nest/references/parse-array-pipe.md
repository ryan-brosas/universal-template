<!-- capsule-v2 -->
# ParseArrayPipe — how are string→array splitting and per-item validation composed, and what does stopAtFirstError actually change?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How do comma-split, primitive coercion, and nested ValidationPipe interact — and why is the fail-fast flag compared STRICTLY to false?

## transform / validatePrimitive / constructor composition
**Path/Symbol:** `packages/common/pipes/parse-array.pipe.ts:transform` (:84-161), `validatePrimitive` (:167-191), `isExpectedTypePrimitive` (:163-165), ctor (:61-75).
**Signature:** `transform(value: unknown, metadata): Promise<any>`; options `{items?, separator? = ',', optional?, stopAtFirstError?, ...ValidationPipeOptions}`.
**Data Shape:** Owns an internal `ValidationPipe({ transform: true, validateCustomDecorators: true, ...options })` — array items get the FULL class-validator treatment.

### Decisive source
```ts
if (!value && !this.options.optional) throw ...('Validation failed (parsable array expected)');
else if (isNil(value) && this.options.optional) return value;
if (!Array.isArray(value)) {
  if (!isString(value)) throw ...;
  value = value.trim().split(this.options.separator || ',');
}
const toClassInstance = (item, index?) => {
  if (this.options.items !== String) { try { item = JSON.parse(item); } catch {} }  // best-effort
  return isExpectedTypePrimitive ? this.validatePrimitive(item, index)
                                 : this.validationPipe.transform(item, { metatype: this.options.items, type: 'query' });
};
if (this.options.stopAtFirstError === false) {
  // strict compare — option is DISABLED by default; only literal false opts into collect-all
  for (let i = 0; i < targetArray.length; i++) {
    try { targetArray[i] = await toClassInstance(targetArray[i]); }
    catch (err) { /* err.getResponse().message[] → `[${i}] ${item}` prefixed */ errors.concat(message); }
  }
  if (errors.length > 0) throw this.exceptionFactory(errors);
  return targetArray;
} else {
  value = await Promise.all((value as unknown[]).map(toClassInstance));   // default: first error throws
}
```

**Flow:** empty/optional gates (note `!value` catches '' AND 0 too) → string ⇒ trim+split → per-item: JSON.parse attempt skipped ONLY for String items → primitive triple (Number via `+` with null/''→NaN trap, String stringify-fallback, Boolean strict typeof) OR delegate to inner ValidationPipe → error collection mode prefixes each message with its `[index]`.
**Invariant:** (1) `stopAtFirstError === false` is a strict comparison because the option's DEFAULT is undefined = fail-fast; truthy values must NOT enable collecting. (2) JSON.parse is best-effort SILENTLY ignored on failure — a plain string item stays a plain string. (3) In collect mode errors carry their index prefix so one exception reports every bad item; in fail-fast mode `Promise.all` rejects with the first. (4) The inner ValidationPipe runs with type 'query' — nested pipes see query-flavored metadata.
**Probe:** `packages/common/test/pipes/parse-array.pipe.spec.ts` (splitting, items validation, stopAtFirstError matrix).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ParseArrayPipe stopAtFirstError validatePrimitive separator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split→coerce→delegate ladder for repeated-parameter parsing; adapt separator/JSON heuristics; omit collect-mode if your error envelope is single-message. Porting wrong: loose-truthing `stopAtFirstError` (inverts semantics), or JSON.parsing without try/catch (crashes on plain tokens).
