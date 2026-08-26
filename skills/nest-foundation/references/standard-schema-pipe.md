<!-- capsule-v2 -->
# StandardSchemaValidationPipe — how does schema-from-metadata validation differ from the class-validator pipe?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Where does the schema come from, when does the pipe skip, and what exactly is returned on success?

## transform / validate / toValidate / formatIssueMessages
**Path/Symbol:** `packages/common/pipes/standard-schema-validation.pipe.ts:transform` (:122-136), `validate` (:162-170), `toValidate` (:145-151), `formatIssueMessages` (:104-113).
**Signature:** `async transform<T = any>(value: T, metadata: ArgumentMetadata): Promise<T>`; `protected validate<T>(value, schema: StandardSchemaV1, options?): Promise<StandardSchemaV1.Result<T>> | Result<T>`.
**Data Shape:** Schema rides in `metadata.schema` (Standard Schema v1 — anything exposing `'~standard'.validate`); options `{ transform = true, validateCustomDecorators = false, validateOptions?, exceptionFactory?, errorHttpStatusCode = 400 }`. Issue shape: `{ path?: PropertyKey[], message: string }`.

### Decisive source
```ts
const schema = metadata.schema;
if (!schema || !this.toValidate(metadata)) return value;   // NO schema ⇒ passthrough

this.stripProtoKeys(value);
const result = await this.validate<T>(value, schema, this.validateOptions);
if (result.issues) throw this.exceptionFactory(result.issues);
return this.isTransformEnabled ? result.value : value;
```

**Flow:** read schema off ARGUMENT metadata (not from a metatype class) → skip entirely when absent or custom-decorator param with `validateCustomDecorators:false` → strip prototype-pollution keys → call the vendor-neutral `'~standard'.validate` (sync OR async result both awaited) → issues ⇒ throw factory-formatted exception → return SCHEMA OUTPUT (`result.value`) by default; original input only when `transform:false`.
**Invariant:** Unlike ValidationPipe, `transform` DEFAULTS TO TRUE and success returns the schema's coerced output — there is no plainToInstance/classToPlain ladder and no primitive-shell swap. Error formatting prefixes `path.join('.') + ': '` per issue; the default `exceptionFactory` maps issues to a flat `string[]` message body via `HttpErrorByCode[status]`. There is no built-in-type skip gate (`toValidate` checks ONLY the custom-decorator flag) because without a schema nothing happens anyway.
**Probe:** `packages/common/test/pipes/standard-schema-validation.pipe.spec.ts` (schema-in-metadata success/issue paths, custom-decorator skipping, path-prefixed messages).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "StandardSchemaValidationPipe metadata.schema ~standard validate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the pattern for pluggable validators: keep the pipe dumb, let param metadata carry the validator, normalize results to `{issues}|{value}`; adapt issue→exception formatting to your envelope; omit the class-validator twin's transform machinery when schemas do coercion natively. Porting wrong: reading the schema from `metatype` instead of `metadata.schema` (there IS no class here — zod/valibot schemas attach directly), or returning the raw input on success and silently discarding schema coercion.
