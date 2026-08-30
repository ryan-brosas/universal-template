<!-- capsule-v2 -->
# Multipart form encoding — how do typed request bodies flatten to FormData with array-key conventions both API styles accept?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What are the null/array/bracket rules, and when must the bracket convention be disabled?

## convertToFormData
**Path/Symbol:** `packages/provider-utils/src/convert-to-form-data.ts:convertToFormData` (:32-61).
**Signature:** `<T extends Record<string, unknown>>(input: T, options?: {useArrayBrackets?: boolean}): FormData`.
**Data Shape:** null/undefined values are SKIPPED (not sent); single-element arrays append under the bare key; multi-element arrays append once per element under `key[]` (or bare key when `useArrayBrackets: false`); scalars/Blobs append directly.

### Decisive source
```ts
if (value == null) continue;                        // absent from the wire entirely
if (Array.isArray(value)) {
  if (value.length === 1) { formData.append(key, value[0]); continue; }  // NO brackets for single
  const arrayKey = useArrayBrackets ? `${key}[]` : key;
  for (const item of value) formData.append(arrayKey, item);
  continue;
}
formData.append(key, value);
```

**Flow:** iteration order = object key order → per-value branch as above. Empty arrays contribute nothing.
**Invariant:** The single-vs-multi split is a WIRE-COMPAT rule: several image/audio APIs reject `images[]` when a single file is sent but require repeated keys without brackets elsewhere — hence the opt-out flag rather than a fixed convention. Skipping nulls means "unset" never reaches providers as the string "null"/"undefined". Values are cast to `string | Blob` at append: numbers arrive pre-stringified by FormData semantics.
**Probe:** `packages/provider-utils/src/convert-to-form-data.test.ts:37/:47` (null AND undefined skipped), `:59` ("single-element arrays as single value WITHOUT [] suffix"), `:69/:83` (multi-element with and without brackets), `:100` (empty array adds nothing).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"convertToFormData useArrayBrackets FormData multipart","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the skip-null/single-bare/multi-bracket ladder verbatim including the escape flag; adapt nothing else. Fully direct-test-pinned at this HEAD.
