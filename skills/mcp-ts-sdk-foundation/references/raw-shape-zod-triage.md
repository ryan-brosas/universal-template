<!-- capsule-v2 -->
# Raw-shape detection & zod version triage — when does `{ field: z.string() }` auto-wrap, and which wrong-version input fails loud instead of silently misbehaving?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does the v1-compat raw-shape shorthand on `registerTool`/`registerPrompt` get detected without mistaking other plain objects for it?

## Detection & normalization
**Path/Symbol:** `packages/core-internal/src/util/zodCompat.ts`: `isZodV4Schema` (:12-18), `looksLikeZodV3` (:20-29), `isZodRawShape` (:39-48), `normalizeRawShapeSchema` (:58-80).
**Signature:** `isZodRawShape(obj: unknown): obj is Record<string, z.ZodType>`; `normalizeRawShapeSchema(schema: StandardSchemaWithJSON | Record<string, z.ZodType> | undefined): StandardSchemaWithJSON | undefined`.
**Data Shape:** v4 marker is `'_zod' in v`; v3 marker is `_def.typeName: string` with NO `_zod`; empty plain object IS a valid raw shape (`[].every()` vacuous truth — matches v1 semantics).

### Decisive source
```ts
// :39-48 three gates before any value check
if (typeof obj !== 'object' || obj === null) return false;
if (isStandardSchema(obj)) return false;          // a wrapped schema wins first
// Require a plain object literal: rejects arrays, Date, Map, RegExp, class instances…
const proto = Object.getPrototypeOf(obj);
if (proto !== Object.prototype && proto !== null) return false;
return Object.values(obj).every(v => isZodV4Schema(v));
```

**Flow:** `undefined` passes through (schema-less tools are legal); raw shapes wrap via `z.object(schema)`; a NON-standard object whose values LOOK like zod 3 throws a TypeError naming the fix ("Import from `zod/v4` … or wrap with `z.object({...})` yourself"); any Standard Schema passes through untouched — per-vendor conversion quirks belong to standardSchemaToJsonSchema, NOT here ("Gating on `~standard.jsonSchema` here would unreachably front-run that fallback").

**Invariant:** detection order matters — checking values BEFORE the prototype/standard-schema gates would classify a Zod-3-wrapped schema or a Date as a "raw shape" and explode inside `z.object()` with an opaque error. The v3 tripwire exists because zod 3 schemas DO carry `~standard.vendor === 'zod'` (since 3.24) and would otherwise flow into v4-only wrap paths and fail far from the author's code.

**Probe (direct tests):** `packages/core-internal/test/util/zodCompat.test.ts` describe 'isZodRawShape' (:7) + 'normalizeRawShapeSchema' (:48) pin plain-object acceptance, array/class rejection, v3 TypeError, passthrough of standard schemas.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "isZodRawShape normalizeRawShapeSchema zod", limit: 3 });
```

## Verdict
Adopt gate ordering + loud v3 failure; adapt error copy to your DX conventions; omit the raw-shape shorthand entirely if your API takes only full schemas.
