<!-- capsule-v2 -->
# ValidationPipe.transform — what does a validated argument come back as, and which value-reverting branches must not be collapsed?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** After class-validator passes, does the caller get the class instance, the plain object, or the original primitive — and why are there three separate "revert" branches?

## transform / createExceptionFactory / toValidate
**Path/Symbol:** `packages/common/pipes/validation.pipe.ts:transform` (:140-210), `createExceptionFactory` (:212-234), `toValidate` (:236-243), `transformPrimitive` (:245-277), `toEmptyIfNil` (:279-297).
**Signature:** `async transform(value: unknown, metadata: ArgumentMetadata): Promise<any>`; `protected toValidate(metadata): boolean`; `protected transformPrimitive(value, metadata): unknown`.
**Data Shape:** `metadata = { type: 'body'|'query'|'param'|'custom', metatype, data?, schema? }`; options destructure keeps `...validatorOptions` rest; module-scope `classValidator`/`classTransformer` vars are assigned in the CONSTRUCTOR then awaited at first `transform`.

### Decisive source
```ts
// toValidate — skip ALL JS built-in metatypes and nil:
const types = [String, Boolean, Number, Array, Object, Buffer, Date];
return !types.some(t => metatype === t) && !isNil(metatype);

// no metatype or nothing to validate → only primitive-coerce when transform enabled:
if (!metatype || !this.toValidate(metadata)) {
  return this.isTransformEnabled ? this.transformPrimitive(value, metadata) : value;
}

// primitive values can't carry decorator metadata → swap in a fake shell for validation:
if (isCtorNotEqual && !isPrimitive) {
  entity.constructor = metatype;              // repair identity on objects
} else if (isCtorNotEqual) {
  entity = { constructor: metatype };          // TEMPORARY shell for primitives
}
...
if (isPrimitive) entity = originalEntity;      // ALWAYS revert primitives after validation
...
const shouldTransformToPlain = Object.keys(this.validatorOptions).length > 1;
return shouldTransformToPlain
  ? classTransformer.classToPlain(entity, this.transformOptions)
  : value;
```

**Flow:** expectedType overrides metadata.metatype → skip-gate (`toValidate`) → await lazy-loaded validator/transformer → `toEmptyIfNil` (nil + class metatype ⇒ `{}`, nil + non-class metatype ⇒ `''` because SWC throws on `{}` — #12680) → stripProtoKeys → `plainToInstance` → constructor-repair/primitive-shell swap → `validate` → errors ⇒ `throw exceptionFactory(errors)` → revert ladder: undefined-original+empty-entity ⇒ original (#14430 SWC artifact), primitive ⇒ originalEntity, transform-off && was-nil ⇒ originalValue, else classToPlain ONLY when extra validatorOptions exist beyond the injected `forbidUnknownValues: false` default.
**Invariant:** (1) `validatorOptions` is seeded with `{ forbidUnknownValues: false }` (#10683 — newer class-validator made `true` the default and would reject every unannotated DTO), so "did the user pass custom validator options?" is tested as `Object.keys(...).length > 1`, NOT `> 0`. Porting with `> 0` silently switches every app into classToPlain mode. (2) Primitives never reach the handler transformed by plainToInstance — the temporary `{constructor: metatype}` shell exists only during `validate()`. (3) `transformPrimitive` runs only for `param|query` WITH `metadata.data`; top-level query/body objects pass through untouched; Boolean coerces any defined falsy to `false`, undefined stays undefined (optional booleans).
**Probe:** `packages/common/test/pipes/validation.pipe.spec.ts` — "should return the value unchanged if optional value is not defined" :71; boolean empty-string→false :355/:405; "when type doesn't match" :553; nested-error flattening :143; grouped format :186-269.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ValidationPipe transform toEmptyIfNil forbidUnknownValues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-branch revert ladder and the `Object.keys > 1` gate as one indivisible contract; adapt `HttpErrorByCode[status]` mapping to your error hierarchy (see parse-pipe-family capsule for the table); omit class-validator specifics only if you have an equivalent decorator-metadata validator — the skip-list `[String,Boolean,Number,Array,Object,Buffer,Date]` must move with it. Porting wrong: returning the class instance when `transform:false` (breaks whitelisting semantics) or validating primitives without the constructor shell (every `@IsInt()` on a `@Query('x') n: number` fails).
