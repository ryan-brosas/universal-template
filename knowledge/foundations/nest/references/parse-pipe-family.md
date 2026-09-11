<!-- capsule-v2 -->
# Parse-pipe family — the shared skeleton: optional gate, strict predicate, HttpErrorByCode throw

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the common contract of ParseInt/ParseBool/ParseUUID/ParseEnum pipes, and where do their predicates differ in strictness?

## ParseIntPipe / ParseBoolPipe / ParseUUIDPipe / ParseEnumPipe / HttpErrorByCode
**Path/Symbol:** `packages/common/pipes/parse-int.pipe.ts:transform` (:64-77), `isNumeric` (:83-89); `parse-bool.pipe.ts:isTrue/isFalse` (:86-97); `parse-uuid.pipe.ts:uuidRegExps` (:52-58); `parse-enum.pipe.ts:isEnum` (:81-91); `packages/common/utils/http-error-by-code.util.ts:HttpErrorByCode` (:50-72).
**Signature:** `async transform(value, metadata): Promise<T | undefined | null>`; options `{ errorHttpStatusCode? = 400, exceptionFactory?, optional? = false }`.
**Data Shape:** All four: nil+optional ⇒ passthrough of the ORIGINAL null/undefined (not a default); failure ⇒ `throw exceptionFactory(message)`.

### Decisive source
```ts
// shared skeleton:
if (isNil(value) && this.options?.optional) return value;
if (!predicate(value)) throw this.exceptionFactory('Validation failed (...)');
return coerce(value);

// INT — regex-anchored integer, THEN isFinite:
['string','number'].includes(typeof value) && /^-?\d+$/.test(String(value)) && isFinite(value as any);
// BOOL — exact duals ONLY ('true'/'false', true/false); '1'/'0' REJECTED:
value === true || value === 'true';   value === false || value === 'false';
// UUID — version-specific variant pin (4/5/7 require [89AB] after 3rd group), case-insensitive:
{ 4: /^[0-9A-F]{8}-...-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i, ..., all: ... }
// ENUM — strip TS reverse-mapping keys (string key whose value maps back to a number):
Object.keys(enumType).filter(k => !(typeof v === 'string' && typeof enumType[v] === 'number')).map(k => enumType[k]).includes(value);
```

**Flow:** each pipe = optional-gate → typed predicate → identity-or-coerced return → exception via `HttpErrorByCode[code]` lookup table (21 status→exception-class entries; only 4xx/5xx codes have classes — passing e.g. 200 throws TypeError at CONSTRUCTION time of the thrown error).
**Invariant:** (1) The enum filter exists because TS string enums compile to objects with BOTH directions; without it `'0'` (a reverse-map KEY) would validate. (2) Int's `/^-?\d+$/` rejects floats and scientific notation BEFORE parseInt — parseInt('3.9') would silently truncate to 3 if the guard were skipped. (3) Bool deliberately does NOT accept truthy/falsy numbers. (4) `optional` returns the ORIGINAL nil rather than throwing — compose with defaultValue handling upstream.
**Probe:** `packages/common/test/pipes/{parse-int,parse-bool,parse-uuid,parse-enum}.pipe.spec.ts` (per-type accept/reject matrices + optional behavior).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ParseIntPipe isNumeric HttpErrorByCode ParseEnumPipe reverse mapping", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skeleton (gate→predicate→coerce→typed-throw) for every coercion pipe you write; adapt predicates but keep their strictness (anchored int regex, exact bool duals, version-pinned UUID variants, reverse-map-stripped enums); omit HttpErrorByCode only for single-status services. Porting wrong: accepting `'1'/'0'` as booleans or unguarded parseInt truncation.
