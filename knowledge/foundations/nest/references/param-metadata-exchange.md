<!-- capsule-v2 -->
# PipesConsumer + ParamsTokenFactory — how does enum-typed param metadata become pipe-flavored string metadata?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Why is there an enum→string exchange before pipes run, and what guarantees the per-argument metadata shape?

## PipesConsumer.apply / applyPipes / ParamsTokenFactory.exchangeEnumForString
**Path/Symbol:** `packages/core/pipes/pipes-consumer.ts:apply` (:8-26), `applyPipes` (:28-38); `packages/core/pipes/params-token-factory.ts:exchangeEnumForString` (:5-16).
**Signature:** `apply(value, metadata: ArgumentMetadata, pipes: PipeTransform[])`; `applyPipes(value, {metatype, type, data, schema}, transforms)`.
**Data Shape:** Internal `RouteParamtypes` NUMERIC enum (BODY/QUERY/PARAM/NEXT/...) → public `Paramtype` STRING union ('body'|'query'|'param'|'custom'); `schema` field carried through untouched for StandardSchemaValidationPipe.

### Decisive source
```ts
public async apply(value, metadata, pipes) {
  const token = this.paramsTokenFactory.exchangeEnumForString(metadata.type as any);
  return this.applyPipes(value,
    { metatype: metadata.metatype, type: token, data: metadata.data, schema: metadata.schema },
    pipes);
}

public async applyPipes(value, { metatype, type, data, schema }, transforms) {
  let result: unknown = value;
  for (const pipe of transforms) {
    result = await pipe.transform(result, { metatype, type, data, schema });  // SEQUENTIAL chain
  }
  return result;
}
```

**Flow:** router execution context resolves raw value via RouteParamsFactory → PipesConsumer translates the numeric route-param kind into the PUBLIC string vocabulary pipes are written against → folds each pipe's output into the next pipe's input, threading an immutable-per-hop metadata object.
**Invariant:** (1) The exchange exists because the internal enum must stay adapter-private while userland pipes switch on `'query'`/`'body'` — leaking numbers would couple every custom pipe to internal constants. (2) Anything not BODY/PARAM/QUERY maps to `'custom'` — which is exactly the flag ValidationPipe.toValidate and StandardSchemaValidationPipe check to skip custom decorator params. (3) The fold is strictly sequential (`await` per hop): a pipe that transforms output feeds the next pipe's input; order of `pipes` arrays is declaration order. (4) `schema` rides along in every hop's metadata although only schema-aware pipes read it.
**Probe:** `packages/core/test/pipes/pipes-consumer.spec.ts` + `params-token-factory.spec.ts` (enum→string matrix); end-to-end ordering pinned by `router-execution-context.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "PipesConsumer applyPipes ParamsTokenFactory exchangeEnumForString", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-vocabulary boundary (internal numeric kinds vs public string types) whenever plugins receive framework enums; adapt token names; omit the schema passthrough if you have no schema-aware consumers. Porting wrong: passing the raw enum into pipes (custom-pipe switch statements silently hit default), or running pipes concurrently (later pipes would see pre-transform values).
