<!-- capsule-v2 -->
# Trace sanitization ladder — how do you bound and redact ARBITRARY values (args, results, errors) before they enter a durable record?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the value-level sanitizer contract that runs BEFORE byte budgets are applied?

## Key-classified walk + structural caps + post-fit prefix shrink
**Path/Symbol:** `src/audit/trace.ts:sanitize` (:184-303), `sanitizeObject` (:305-316), `truncateUtf8` (:102-114), `truncateUtf8Middle` (:116-127), `isSensitiveKey` (:134-151), `isMediaKey`/`isMediaObject` (:153-163), `looksLikeBase64` (:165-182).
**Signature:** `sanitize(input: unknown, maxBytes: number): {value: FabricTraceJsonValue, counts}`; DROP sentinel symbol for key-ordered removal; per-value budgets MAX_STRING_BYTES 16 KiB, MAX_ERROR_BYTES 8 KiB, args/results 64 KiB; structure caps depth 12 / keys 128 / array 128 / nodes 8_192.
**Data Shape:** output restricted to the FabricTraceJsonValue union — JSON-safe by construction (non-finite numbers → `"[non-finite:…]"`, bigint → `"123n"`, undefined/function/symbol → dropped).

### Decisive source
```ts
if (key !== undefined && isSensitiveKey(key)) { counts.redactedValues++; return "[REDACTED]"; }
if (key !== undefined && isMediaKey(key))     { counts.droppedValues++;  return DROP; }
...
if (ancestors.has(value)) { counts.droppedValues++; return "[CIRCULAR]"; }
```
```ts
// second pass: if the WHOLE sanitized value exceeds its budget, keep the
// longest fitting PREFIX of entries (serialized each step) with a 128-byte headroom
const next = { ...output, [childKey]: child };
if (serializedBytes(next) > maxBytes - 128) break;
output[childKey] = child;
```

**Flow:** single walk with an ancestors set (cycle → `[CIRCULAR]`, not a crash): classification order is sensitive-key REDACT → media-key DROP → base64-shaped strings (`data:` URIs or ≥1 KiB length-multiple-of-4 pure-alphabet) → `[OMITTED_BASE64]` → typed scalars normalized → media objects (by type field or image/audio/video MIME) → `[OMITTED_MEDIA]` → recursion under depth/key/array/node caps. Object keys SORTED (byte-stable output regardless of insertion order). Only THEN does the serialized-prefix pass fit the result into its budget with headroom. Errors use middle-truncation (head+tail around `\n…[truncated]\n`) because stack tails matter.
**Invariant:** redaction is a KEY-class decision applied during the walk (sensitive keys die even when their values look innocent), while size handling is a separate measured pass — the two concerns never blur; every action bumps a counter so the record can state what it lost; sorted keys make two equivalent inputs serialize identically.
**Probe:** pinned across the audit suite — `tests/audit-trace.test.ts:799` ("retains bash commands while omitting arbitrary argument and result content"), `:996` ("enforces the total UTF-8 envelope bound with explicit drops"), `:1015` ("is byte-stable when legacy random IDs and timings differ" — determinism of the whole pipeline incl. sorted keys).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "sanitize isSensitiveKey looksLikeBase64 truncateUtf8Middle CIRCULAR OMITTED_MEDIA redactedValues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the walk-time key-class redaction + measured prefix-fit two-pass split, cycle-safe ancestors set, and sorted-key byte stability for ANY bounded-record surface; adapt the sensitive/media vocabularies and budgets; omit the trace-specific type names. Direct tests cited; graph coverage clean.
