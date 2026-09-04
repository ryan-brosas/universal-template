<!-- capsule-v2 -->
# Zod validator + schema-to-TS printer — how do runtime schemas become prompt-facing TypeScript?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does a Zod v4 schema object both validate JSON and print itself as the TypeScript definitions that go into the LLM prompt?

## createZodJsonValidator
**Path/Symbol:** `typescript/src/zod/validate.ts:14-30`.
**Signature:** `createZodJsonValidator<T extends Record<string, z.ZodType>, K extends keyof T & string>(schema: T, typeName: K): TypeChatJsonValidator<z.infer<T[K]> & object>`.
**Data Shape:** schema = named map of Zod types; `getSchemaText()` is LAZY and memoized via `schemaText ??= getZodSchemaAsTypeScript(schema)` (:17) — identity-stable across calls (tested with strictEqual).

### Decisive source
```ts
function validate(jsonObject: object) {
    const result = schema[typeName].safeParse(jsonObject);
    if (!result.success) {
        return error(result.error.issues.map(({ path, message }) => `${path.map(key => `[${JSON.stringify(key)}]`).join("")}: ${message}`).join("\n"));
    }
    return success(result.data as z.infer<T[K]> & object);
}
```
**Flow:** safeParse → issues rendered as `[path][segments]: message` joined by newlines (JSON.stringify'd keys so numeric indices read `[0]`) → multi-issue messages are one error per line, directly consumable by the repair prompt.
**Invariant:** validation returns Zod's PARSED OUTPUT (`result.data`), which may differ from the input (defaults applied, coerced values) — downstream code receives normalized data. The `& object` intersection exists because TypeChat's translator constrains `T extends object` while z.infer may infer non-objects.

## getZodSchemaAsTypeScript
**Path/Symbol:** `typescript/src/zod/validate.ts:80-266`; kind accessors :38-52; precedence :54-69.
**Signature:** `(schema: Record<string, z.ZodType>): string`.
**Data Shape:** named entries emit `interface Name {...}` for objects else `type Name = ...;`; inner references resolve through a name table keyed by `getTypeIdentity` — shape for objects, `entries` for enums, `options` for unions, the type itself otherwise (:42-52).

### Decisive source
```ts
case "union": { // covers both z.union() and z.discriminatedUnion() — Zod v4 merged discriminated unions into the regular union type kind ("ZodDiscriminatedUnion" in v3); both have an `options` array
    const unionDef = type._zod.def as z.core.$ZodDiscriminatedUnionDef | z.core.$ZodUnionDef;
    return appendUnionOrIntersectionTypes(unionDef.options as readonly z.ZodType[], TypePrecedence.Union);
}
```
**Flow:** writer threads `{result, startOfLine, indent}` closures for 4-space pretty printing; parenthesization driven by a precedence lattice Union(0) < Intersection(1) < Object(2) — an element prints parenthesized when its precedence < the context minimum (so `A & B` inside an array becomes `(A & B)[]`).
**Invariant:** optional handling is asymmetric ON PURPOSE: standalone `z.optional(T)` prints `T | undefined`, but INSIDE an object/tuple it prints `name?: T` and unwraps to innerType (:194-208/:234-237). Optional-wrapper `.describe()` comments hoist ABOVE the field line; plain-field descriptions go INLINE after `;`. Unhandled kinds fall through to `any` (z.nan() pinned by test). Discriminated unions need NO special case at this pin because Zod v4 folds them into kind "union" — a porter importing v3 assumptions will add dead code or miss options arrays.
**Probe:** `grep -c 'ZodDiscriminatedUnion' typescript/src/zod/validate.ts` (=3); `grep -c 'schema[typeName].safeParse' typescript/src/zod/validate.ts` (=1); live pins `typescript/test/zod.test.ts`: :86-91 `b?: string` with NO `| undefined`; :101-108 wrapper-description placement both directions; :218-222 v4 array-overload literal union; :344-352 unknown-kind→any.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"zod schema typescript getZodSchemaAsTypeScript","limit":4}'
// rank1 Function typescript/src/zod/validate.ts 80-266 (has_more true — page if enumerating)
```

## Verdict
Adopt the two-surface contract (validator + printer off ONE schema) — it's what keeps prompts and validation in sync; adapt issue formatting to host error conventions; omit enum/literal edge branches only if your schema language lacks them. Direct tests cover every printer branch incl v4-specific overloads at this pin.
