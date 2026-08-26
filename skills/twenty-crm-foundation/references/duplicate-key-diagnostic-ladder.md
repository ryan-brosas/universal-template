<!-- capsule-v2 -->
# duplicate-key-diagnostic-ladder

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/api/graphql/workspace-query-runner/utils/handle-duplicate-key-error.util.ts` (+ `parse-postgres-constraint-error.util.ts`, `find-conflicting-record.util.ts`)
- Symbol: `handleDuplicateKeyError` / `parsePostgresConstraintError` / `findConflictingRecord`
- Lines: handle-duplicate-key 17-67; parse util 21-41; find-conflicting 11-76
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.api.graphql.workspace-query-runner.utils.handle-duplicate-key-error.util.handleDuplicateKeyError`

## Signature & Data Shape
```typescript
type PostgreSQLError = QueryFailedError & { detail?: string; driverError?: Error & { detail?: string } };
type ParsedConstraintError = { columnName: string; conflictingValue: string };

export const handleDuplicateKeyError = async (
  error: PostgreSQLError,
  objectMetadata: FlatObjectMetadata,
  internalContext: WorkspaceInternalContext,
  entityManager: WorkspaceEntityManager,
): Promise<TwentyORMException & {
  conflictingRecordId?: string;
  conflictingObjectNameSingular?: string;
}>;
```

## Decisive Source Excerpt
```typescript
const parsedError = parsePostgresConstraintError(error);
// parsePostgresConstraintError:
const detailMatch = errorDetail.match(/Key \(([^)]+)\)=\(([^)]+)\)/);
if (!detailMatch) return null;
const columnName = detailMatch[1].replace(/^[\"']|[\"']$/g, '');   // strip quoting chars
const conflictingValue = detailMatch[2];

// back in handleDuplicateKeyError — unparseable detail degrades to generic message:
if (!parsedError) {
  return new TwentyORMException(
    DUPLICATE_ENTRY_DETECTED_MESSAGE,
    TwentyORMExceptionCode.DUPLICATE_ENTRY_DETECTED,
    { userFriendlyMessage: DUPLICATE_ENTRY_USER_FRIENDLY_MESSAGE },
  );
}

const conflictingRecord = await findConflictingRecord(
  parsedError.columnName, parsedError.conflictingValue,
  objectMetadata, internalContext, entityManager,
);

const fieldLabel = conflictingRecord?.fieldLabel;
const userFriendlyMessage = fieldLabel
  ? msg`This ${fieldLabel} value is already in use. Please check your data and try again.`
  : DUPLICATE_ENTRY_USER_FRIENDLY_MESSAGE;
```

## Flow
1. PG emits `23505` with a `detail` field shaped `Key (<col>)=(<value>) already exists`. Regex-parse it (strip surrounding quotes from the column name); no match → generic duplicate message, never a crash.
2. `findConflictingRecord`: map the SQL column name BACK to the metadata field by matching unique fields first by plain name, then by composite-column convention `${field.name}${capitalize(property.name)}` for composite types whose `isIncludedInUniqueConstraint` property produced the column.
3. If a field matches, run a **permission-bypassing** lookup (`shouldBypassPermissionChecks: true`) filtered on `"${columnName}" = :value AND "deletedAt" IS NULL`; wrap in try/catch returning null on any failure so diagnostics can never mask the original constraint error.
4. Compose the user-facing message around the FIELD LABEL (`This Email value is already in use…`), attach `conflictingRecordId` + object name to the exception for UI deep-links.

## Invariant
Duplicate-key errors must surface as typed domain exceptions carrying a field-label-level message and an optional record pointer, while ALL diagnostic machinery is fail-open: parse failure → generic message; lookup failure → null; permission checks bypassed ONLY inside this read-only diagnostic query. Raw driver strings never reach clients.

## Direct-Test Probe
```bash
grep -n 'Key \\(' packages/twenty-server/src/engine/api/graphql/workspace-query-runner/utils/parse-postgres-constraint-error.util.ts   # => :29
grep -n 'shouldBypassPermissionChecks: true\|deletedAt" IS NULL' packages/twenty-server/src/engine/api/graphql/workspace-query-runner/utils/find-conflicting-record.util.ts   # => :55,:58
grep -rn 'handleDuplicateKeyError' packages/twenty-server/src/engine/twenty-orm/error-handling/__tests__/compute-twenty-orm-exception.spec.ts | head -3   # => delegation pin :141 region
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"handleDuplicateKeyError"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the whole three-file ladder whenever a multi-tenant app maps raw unique-violations onto user-facing messages; the composite-field column-name convention and the fail-open try/catch are what porters get wrong.
