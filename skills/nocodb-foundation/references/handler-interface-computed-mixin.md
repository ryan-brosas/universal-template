<!-- capsule-v2 -->
# Interface contract + CreatedBy mixins — what must every handler implement, and how do auto-populated columns reuse User SQL while refusing writes?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What is the exact FilterOperationResult protocol, and how do CreatedBy/LastModifiedBy get User-family filtering with Computed-style write rejection?

## field-handler.interface.ts + created-modified-by.handlers.ts
**Path/Symbol:** `field-handler.interface.ts` — ConditionParser :9; FilterOptions :20-31 (throwErrorIfInvalid/baseModel/depth documented "required by formula and lookup" :22-29); FilterOperationResult :34 `{clause, rootApply?}`; FilterOperationHandlers op table :54-93 (with the null/empty/blank split rationale docstring :61-72 — "Collapsing all three ... broke the filter parity tests" :66-70); FieldHandlerInterface :107-162. `user/created-modified-by.handlers.ts` (39L) — withComputedParseUserInput mixin :15-28; CreatedBy aliases :29-38.
**Signature:** `withComputedParseUserInput<T extends new (...a:any[])=>any>(Base: T) => class extends Base { async parseUserInput(): { value: undefined } }` — a class-factory mixin, not inheritance duplication.
**Data Shape:** clause closures receive the qb LATER (deferred application); rootApply handles statements that must land OUTSIDE the where-tree (CTE scaffolding).

### Decisive source
```ts
// interface :63-70 — why three ops exist that look identical:
// `null` / `notnull` — match strictly on `IS NULL` / `IS NOT NULL`. Distinct
// from `blank` / `notblank`, which also fold empty-string `''` ... Collapsing
// all three into `filterBlank` made null/empty/blank behave identically and
// broke the filter parity tests for LongText / SingleSelect / MultiSelect on PG.
// created-modified-by :18-22:
// Mix-in for CreatedBy / LastModifiedBy columns: same filter behavior as the
// corresponding User handler ..., but `parseUserInput` returns undefined since
// these columns are auto-populated by the system and never accept user writes.
```

**Flow:** handlers return deferred results; FieldHandler composes them via getLogicalOpMethod; verify paths share FilterVerificationResult `{isValid, errors?}`. CreatedBy = mixin(UserGeneralHandler) keeping display-name substitution for like/nlike + sort but rejecting writes; LastModifiedBy aliases are literally the SAME exports (`export const LastModifiedByGeneralHandler = CreatedByGeneralHandler`) because behavior is structurally identical.
**Invariant:** (1) The mixin preserves dialect wiring: CreatedByPgHandler = mixin(UserPgHandler) so PG's replace_delimited primitive still applies. (2) Export aliasing means adding behavior to CreatedBy automatically reaches LastModifiedBy — splitting them would fork silently. (3) parseUserInput returning undefined (not throwing) is the computed-column convention: parseDataDbValue skips undefined cells without error.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "broke the filter parity tests" (field-handler.interface.ts :70); search_graph resolves `withComputedParseUserInput Function ... created-modified-by.handlers.ts 15-28` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "FilterOperationHandlers", limit: 5 });
```

## Verdict
Adopt the deferred-result protocol + mixin-over-copy for system columns; adapt the op vocabulary to your API surface; omit nothing. Caveat: no direct tests at pin.
