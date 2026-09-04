<!-- capsule-v2 -->
# sql-identifier-escaping

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/workspace-manager/workspace-migration/utils/remove-sql-injection.util.ts`
- Symbol: `escapeIdentifier` / `escapeLiteral` / `removeSqlDDLInjection` / `assertSafeTsVectorExpression`
- Lines: 1-14 (stripper), 16-23 (escapeIdentifier), 25-56 (tsvector guard), 59-88 (escapeLiteral)
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.workspace-manager.workspace-migration.utils.remove-sql-injection.util.escapeIdentifier`

## Signature & Data Shape
```typescript
export const removeSqlDDLInjection: (value: string) => string;   // keep [a-zA-Z0-9_] only
export const escapeIdentifier: (identifier: string) => string;   // PG standard quoting
export const escapeLiteral: (value: string) => string;           // E-prefix aware
export const assertSafeTsVectorExpression: (expression: string) => void;
```

## Decisive Source Excerpt
```typescript
export const escapeIdentifier = (identifier: string): string => {
  if (identifier.includes('\0')) {
    throw new Error('Null bytes are not allowed in PostgreSQL identifiers');
  }
  return '"' + identifier.replace(/"/g, '""') + '"';
};

// Strips all characters except [a-zA-Z0-9_].
// Use ONLY for generating safe identifier names (e.g. enum names from table+column).
// For SQL escaping, use escapeIdentifier or escapeLiteral instead.
export const removeSqlDDLInjection = (value: string): string =>
  value.replace(/[^a-zA-Z0-9_]/g, '');

export const escapeLiteral = (value: string): string => {
  if (value.includes('\0')) { /* throw — null bytes forbidden in literals */ }
  let hasBackslash = false;
  let escaped = "'";
  for (const char of value) {
    if (char === "'") escaped += "''";
    else if (char === '\\') { escaped += '\\\\'; hasBackslash = true; }
    else escaped += char;
  }
  escaped += "'";
  if (hasBackslash) escaped = 'E' + escaped;   // standard_conforming_strings safety
  return escaped;
};
```

## Flow
1. **Two distinct defense layers, never interchangeable**: `removeSqlDDLInjection` is a WHITELIST stripper for GENERATING names (enum type name = table+column concat); `escapeIdentifier`/`escapeLiteral` are standard-conforming QUOTERS for embedding user-influenced strings into DDL/DML. The source comment explicitly forbids using the stripper where quoting is needed.
2. `escapeIdentifier`: reject null bytes (loud throw), wrap in double quotes, double internal `"`. Case preservation comes free — quoted identifiers are case-sensitive.
3. `escapeLiteral`: double `'`, DOUBLE backslashes, and prefix `E` when any backslash present so escapes are honored under `standard_conforming_strings=on`.
4. tsvector GENERATED-column expressions get a separate state-machine validator (`isSafeTsVectorExpression`): forbidden tokens `\0 ; -- /* */ $` plus a code/string/identifier context scanner with balanced-paren check — asserted at the DDL sink in `buildSqlColumnDefinition`.

## Invariant
Dynamic multi-tenant DDL must quote identifiers with the PostgreSQL doubling rule and NEVER rely on character stripping alone for values that reach SQL as identifiers or literals. Null bytes are rejected outright (Postgres rejects them anyway; failing early beats driver-level corruption). Backslash-bearing literals require the `E''` prefix or the backslashes land literally.

## Direct-Test Probe
- File: `packages/twenty-server/src/engine/workspace-manager/workspace-migration/utils/__tests__/remove-sql-injection.util.spec.ts`
- Suites/pins: `describe('escapeIdentifier')` (:17) incl. `it('should handle SQL injection attempts in identifiers')` (:41); `describe('escapeLiteral')` (:48) incl. `it('should escape backslashes and add E prefix')` (:62); `describe('assertSafeTsVectorExpression')` (:92)

```bash
grep -n 'my""table\|it'"'"'s' packages/twenty-server/src/engine/workspace-manager/workspace-migration/utils/__tests__/remove-sql-injection.util.spec.ts | head -4   # => doubling pins :22,:53
grep -c "it(" packages/twenty-server/src/engine/workspace-manager/workspace-migration/utils/__tests__/remove-sql-injection.util.spec.ts   # => 15
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"escapeIdentifier"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt verbatim — three small pure functions that every workspace-DDL path composes. The stripper-vs-quoter distinction is the porting trap: stripping a literal breaks its content; quoting an identifier with the stripper loses case and characters.
