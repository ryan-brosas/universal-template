<!-- capsule-v2 -->
# Exception filter selection — catch-all wildcard, first-match-wins, and the reversed wiring nobody expects

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Given a filter list, which filter handles an exception, why does registration call `.reverse()`, and how are non-HttpException errors classified?

## selectExceptionFilterMetadata + ExceptionsHandler
**Path/Symbol:** `packages/common/utils/select-exception-filter-metadata.util.ts:selectExceptionFilterMetadata` (:3-13); `packages/core/exceptions/exceptions-handler.ts:invokeCustomFilters` (:22-39); `packages/core/router/router-exception-filters.ts:create` (:25-47).
**Signature:** `selectExceptionFilterMetadata<T>(filters: ExceptionFilterMetadata[], exception: T): ExceptionFilterMetadata | undefined`; `invokeCustomFilters(exception, ctx): boolean`.
**Data Shape:** `ExceptionFilterMetadata = { func: (exception, ctx) => void, exceptionMetatypes: Type[] }` — func is pre-bound `instance.catch`.

### Decisive source
```ts
// selection: EMPTY metatype list = catch-all; Array.find = FIRST match wins
filters.find(({ exceptionMetatypes }) =>
  !exceptionMetatypes.length ||
  exceptionMetatypes.some(ExceptionMetaType => exception instanceof ExceptionMetaType));

// handler: custom filters first, base filter as fallback
public next(exception, ctx) {
  if (this.invokeCustomFilters(exception, ctx)) return;
  super.catch(exception, ctx);
}

// wiring: metadata arrives global→type→method; REVERSED before storage
exceptionHandler.setCustomFilters(filters.reverse());
```

**Flow:** RouterExceptionFilters.create composes filters via ContextCreator (global concat class concat method) → `.reverse()` so METHOD-level filters end up FIRST at selection time → at throw time `find` picks the first accepting filter → unclaimed exceptions fall to BaseExceptionFilter.catch.
**Invariant:** Selection is first-match-wins with empty-metatype catch-all — order IS semantics. The reversal happens ONCE at wiring; a porter who reverses again at dispatch inverts priority (method filters lose to globals). BaseExceptionFilter classifies unknowns via `isHttpError`: FastifyError shape (`constructor.name==='FastifyError' && code:string && statusCode:number`) or http-errors signature (`expose:boolean && status===statusCode && instanceof Error`) or bare `{statusCode,message}`; unknown → 500 + generic message, and logging is suppressed for IntrinsicException subclasses.
**Probe:** `packages/common/test/utils/select-exception-filter-metadata.util.spec.ts` ("should pass error handling to first suitable error handler"); `packages/core/test/router/router-exception-filters.spec.ts` create-with-filters.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ExceptionsHandler invokeCustomFilters selectExceptionFilterMetadata", limit: 5 });
```

## Verdict
Adopt catch-all-as-empty-list + find-first selection + single-reversal-at-wiring; adapt error-shape sniffing to your framework's error taxonomy; omit IntrinsicException quiet-logging only if you lack internal error classes. Porting wrong: double-reversal or per-dispatch reordering silently flips which filter owns an exception.
