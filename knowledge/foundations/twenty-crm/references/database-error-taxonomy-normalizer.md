<!-- capsule-v2 -->
# database-error-taxonomy-normalizer

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/error-handling/compute-twenty-orm-exception.ts`
- Symbol: `computeTwentyORMException` (+ `POSTGRESQL_ERROR_CODES`, `CONSTRAINT_VIOLATION_USER_FRIENDLY_MESSAGES`)
- Lines: 24-89 (whole function); codes table `engine/api/graphql/workspace-query-runner/constants/postgres-error-codes.constants.ts`
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.error-handling.compute-twenty-orm-exception.computeTwentyORMException`

## Signature & Data Shape
```typescript
export const computeTwentyORMException: (
  error: Error,
  objectMetadata?: FlatObjectMetadata,
  entityManager?: WorkspaceEntityManager,
  internalContext?: WorkspaceInternalContext,   // all three optional — UNIQUE_VIOLATION needs them
) => Promise<Error | TwentyORMException>;
```

## Decisive Source Excerpt
```typescript
if (error instanceof QueryFailedError) {
  if (error.message.includes(QUERY_READ_TIMEOUT_MESSAGE)) {
    return new TwentyORMException(QUERY_READ_TIMEOUT_MESSAGE,
      TwentyORMExceptionCode.QUERY_READ_TIMEOUT,
      { userFriendlyMessage: QUERY_READ_TIMEOUT_USER_FRIENDLY_MESSAGE });
  }

  const errorCode = (error as QueryFailedErrorWithCode).code;

  if (errorCode === POSTGRESQL_ERROR_CODES.UNIQUE_VIOLATION &&
      isDefined(objectMetadata) && isDefined(entityManager) && isDefined(internalContext)) {
    return await handleDuplicateKeyError(error, objectMetadata, internalContext, entityManager);
  }

  if (errorCode === POSTGRESQL_ERROR_CODES.INVALID_TEXT_REPRESENTATION) {
    return new TwentyORMException(error.message, TwentyORMExceptionCode.INVALID_INPUT);
  }

  if (isDefined(errorCode) && errorCode in CONSTRAINT_VIOLATION_USER_FRIENDLY_MESSAGES) {
    return new TwentyORMException(error.message, TwentyORMExceptionCode.INVALID_INPUT,
      { userFriendlyMessage: CONSTRAINT_VIOLATION_USER_FRIENDLY_MESSAGES[errorCode] });
  }

  if (isDefined(errorCode) && Object.values(POSTGRESQL_ERROR_CODES).includes(errorCode)) {
    throw new PostgresException('Data validation error.', errorCode);
  }
  throw error;      // known-but-unhandled code → rethrow; unknown code → rethrow original
}
return error;       // not a driver error → untouched
```

## Flow
1. Only `QueryFailedError` instances enter the ladder; everything else passes through unchanged.
2. Timeout detection is MESSAGE-based (`57014` arrives with a driver-specific message), checked BEFORE code extraction.
3. `23505` UNIQUE_VIOLATION escalates to the metadata-aware diagnostic ladder ONLY when full context is provided — otherwise falls through to the generic constraint branch (graceful degradation of diagnostics, never of correctness).
4. `22P02` INVALID_TEXT_REPRESENTATION → INVALID_INPUT keeping the raw message (it names the offending value shape).
5. Constraint family (`23502` NOT_NULL / `23503` FOREIGN_KEY / `23514` CHECK / `23001` RESTRICT…) → INVALID_INPUT + per-code localized user-friendly message from the constants table.
6. Any OTHER known Postgres code → generic `PostgresException('Data validation error.', code)`; unknown/absent code → rethrow the ORIGINAL error.

## Invariant
Driver exceptions must normalize into typed domain exceptions with sanitized user-facing messages before crossing the API boundary; schema names and raw SQL dumps never leak. The mapping order is semantic: timeout-by-message first, then metadata-rich duplicate handling, then per-code tables, then catch-all, then honest rethrow — each branch narrower than the last.

## Direct-Test Probe
- File: `packages/twenty-server/src/engine/twenty-orm/error-handling/__tests__/compute-twenty-orm-exception.spec.ts`
- Suite: `describe('computeTwentyORMException')` (:35)
- Pins: NOT_NULL (:40), FOREIGN_KEY (:56), RESTRICT (:72), preserve-original-message (:88), CHECK→catch-all PostgresException (:101), INVALID_TEXT_REPRESENTATION (:113), QUERY_READ_TIMEOUT (:130), delegate-to-handleDuplicateKeyError (:141), known-code-without-dedicated-handling (:171), unknown-code-rethrow (:185), non-QueryFailedError passthrough (:191)

```bash
grep -c "it(" packages/twenty-server/src/engine/twenty-orm/error-handling/__tests__/compute-twenty-orm-exception.spec.ts   # => 11
grep -n "UNIQUE_VIOLATION" packages/twenty-server/src/engine/api/graphql/workspace-query-runner/constants/postgres-error-codes.constants.ts   # => :96
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"computeTwentyORMException"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the ordered normalization ladder verbatim; the ordering and the optional-context degradation of the duplicate-key branch are what naive ports flatten incorrectly.
