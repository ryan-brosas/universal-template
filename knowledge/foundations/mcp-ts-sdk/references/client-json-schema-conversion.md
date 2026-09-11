<!-- capsule-v2 -->
# Client JSON-Schema conversion surface — how does a raw JSON Schema become a StandardSchemaV1 validator on the client, and which runtime gets which default?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What exactly does `fromJsonSchema` do at each layer (core-internal kernel vs client re-export), and how is the default validator chosen per runtime?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/validators/fromJsonSchema.ts` whole file (:1-43, kernel); `packages/client/src/fromJsonSchema.ts` whole file (:1-9, re-export + lazy default); runtime shims `packages/client/src/shimsNode.ts` / `shimsBrowser.ts` / `shimsWorkerd.ts` (export-condition selection); graph nodes `typescript-sdk.packages.client.src.fromJsonSchema.fromJsonSchema` and `typescript-sdk.packages.core-internal.src.validators.fromJsonSchema.fromJsonSchema`. PATH CORRECTION: pass-9 state.md named `packages/client/src/client/fromJsonSchema.ts` — the file lives one level up at `packages/client/src/fromJsonSchema.ts`.
**Signature:** `fromJsonSchema<T = unknown>(schema: JsonSchemaType, validator?: jsonSchemaValidator): StandardSchemaWithJSON<T, T>` (client; the core-internal twin requires the validator).
**Data Shape:** input is a raw JSON Schema object (TypeBox output or hand-written); output is a `StandardSchemaV1` wrapper with `vendor: 'mcp'` whose `jsonSchema.input/output` both return the SAME schema object; callback args are typed `unknown` (raw JSON Schema carries no TS types) — cast at the call site via the generic.

### Decisive source
```ts
// core-internal :27-43 — the kernel: wrap, do not transform
export function fromJsonSchema<T = unknown>(schema: JsonSchemaType, validator: jsonSchemaValidator): StandardSchemaWithJSON<T, T> {
    const check = validator.getValidator<T>(schema);
    return {
        '~standard': {
            version: 1,
            vendor: 'mcp',
            jsonSchema: {
                input: () => schema as Record<string, unknown>,
                output: () => schema as Record<string, unknown>
            },
            validate: (data: unknown): StandardSchemaV1.Result<T> => {
                const result = check(data);
                return result.valid ? { value: result.data } : { issues: [{ message: result.errorMessage }] };
            }
        }
    };
}
// client :5-9 — lazy MODULE-LEVEL default, shared across all call sites
let _defaultValidator: jsonSchemaValidator | undefined;
export function fromJsonSchema<T = unknown>(schema: JsonSchemaType, validator?: jsonSchemaValidator): StandardSchemaWithJSON<T, T> {
    return coreFromJsonSchema<T>(schema, validator ?? (_defaultValidator ??= new DefaultJsonSchemaValidator()));
}
// shimsNode.ts — export condition "node": AjvJsonSchemaValidator
// shimsBrowser.ts / shimsWorkerd.ts — "browser"/"workerd": CfWorkerJsonSchemaValidator;
// shimsWorkerd.ts additionally calls preloadSchemas() at module scope (isolate warm-up economics)
```

**Flow:** call site passes raw JSON Schema (+ optional explicit validator) → client layer fills in the runtime default only when no validator was given → core-internal compiles it once via `validator.getValidator(schema)` and closes over the compiled `check` → every `validate(data)` maps the engine's `{valid, data, errorMessage}` onto the Standard SchemaV1 `{value}` / `{issues:[{message}]}` shape. Runtime default selection happens at IMPORT time through package.json export conditions (Node ⇒ AJV, browser/workerd ⇒ Cloudflare CfWorker), not per call. The Client's own tool-output validation is a SEPARATE path: the constructor builds an immediate per-instance `DefaultJsonSchemaValidator` (client.ts :638) and compiles output schemas lazily against the response-cache substrate stamp (see jsonSchemaValidatorOverride tests below).

**Invariant:** the wrapper is a pure adapter — it never transforms the schema (input/output both hand back the same object), so schema identity survives into any consumer that reads `~standard.jsonSchema`; validation failures collapse to a SINGLE issue carrying the engine's `errorMessage` (no issue-array fan-out); the workerd shim's module-scope `preloadSchemas()` is load-bearing for billed-CPU economics (schema-preload-economics.md) while Node/browser stay lazy.

**Probe:** `packages/client/test/client/jsonSchemaValidatorOverride.test.ts` :200-214 (`fromJsonSchema uses an explicitly supplied custom validator` — RecordingValidator sees the exact schema once and the validated value), :65-115 (Client-level custom validator: derived view re-compiles lazily on first callTool against the cached tools/list stamp, then memoizes — populating the cache alone does not compile), :163-199 (compile-error lifecycle held on the substrate stamp: re-advertising without the bad outputSchema clears it; a one-off `toolDefinition` never poisons the listed tool).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.core-internal.src.validators.fromJsonSchema.fromJsonSchema" });
```

## Verdict
Adopt the two-layer split verbatim (kernel requires the validator; the package re-export owns the runtime default) and the single-issue failure collapse; adapt the export-condition shim table to your host's runtimes; omit any schema transformation in the wrapper — consumers that read `~standard.jsonSchema` expect the original object back. Coverage caveat: the workerd preload line is source-visible but its economics are pinned by core-internal's preload tests, not a client test.
