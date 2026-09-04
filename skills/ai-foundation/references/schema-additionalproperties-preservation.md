<!-- capsule-v2 -->
# JSON-Schema additionalProperties preservation — when is `additionalProperties: false` the WRONG strictness?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Strict-mode providers need `additionalProperties:false`, but what happens to Zod 4 `record(valueSchema)` / `catchall` schemas that EXPRESS a value type there?

## Schema-aware strictness sweep
**Path/Symbol:** `packages/provider-utils/src/add-additional-properties-to-json-schema.ts` (visitor, ~:1–60); fix #18046 changed one assignment.
**Signature:** recursive `visit(jsonSchema)` — mutates in place, returns schema.
**Data Shape:** JSON-Schema objects; `additionalProperties` may be absent | boolean | SCHEMA.

### Decisive source
```ts
- jsonSchema.additionalProperties = false;
+ const { additionalProperties } = jsonSchema;
+ jsonSchema.additionalProperties =
+   additionalProperties != null && typeof additionalProperties !== 'boolean'
+     ? visit(additionalProperties)   // keep semantics: recurse into the VALUE schema
+     : false;                        // plain open-object → strict
```

**Flow:** the sweep walks every object schema; when `additionalProperties` holds a SUBSCHEMA (Zod 4's `z.record(T)` / `.catchall(T)` compile to exactly that), overwriting it with `false` ERASED the value constraint — providers then rejected valid keys or accepted anything. Now subschemas are recursed (gaining their own `additionalProperties:false` on nested objects) while absent/boolean cases still become `false`.
**Invariant:** Strictification must be SEMANTICS-PRESERVING — never replace a schema-valued keyword with a boolean constant. The same rule generalizes to any "make it strict" pass over user-authored schemas.
**Probe:** deterministic probe: `grep -cF "typeof additionalProperties !== 'boolean'" packages/provider-utils/src/add-additional-properties-to-json-schema.ts` → `1`. Direct tests: `add-additional-properties-to-json-schema.test.ts` (new suite from #18046).
**Retrieve:** verified live @9d9a73f via grep pin; graph anchor on the visitor function name.

## Verdict
Adopt schema-preserving strictification; adapt only the trigger condition (which providers demand `false`); pairs with `flexible-schemas.md` which owns the conversion facade this visitor sits behind.
