<!-- capsule-v2 -->
# PG capability probing + identifier hashing — how does code adapt to Postgres feature gaps and 63-char identifier limits without version sniffing?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is `pg_input_is_valid` availability detected, and how are over-long identifiers kept collision-free?

## Capability-by-execution + FNV-1a hash suffixing
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/utils/detectPgCapability.ts` (69L) + `shared/sqlIdentifiers.ts` (61L); direct tests `utils/detectPgCapability.spec.ts`, `shared/db.spec.ts` (identifier pins).
**Signature:** `hasPgInputIsValid(db): Promise<boolean>`; `assertTypeValidationPolyfill(db): Promise<void>`; `toPostgresIdentifierWithHash(name): string`; `splitSchemaQualifiedTableName(name)`; `toQualifiedIdentifierLiteral(schema?, table): QualifiedIdentifierLiteral` (branded string).
**Data Shape:** hash = FNV-1a 32-bit → base36, zero-padded to 7 chars; cap = `POSTGRES_IDENTIFIER_MAX_LENGTH = 63`.

### Decisive source
```ts
// detectPgCapability — probe by EXECUTION, classify the error
await sql`SELECT pg_input_is_valid('1','numeric')`.execute(db);
// only 42883 ("function does not exist") ⇒ false; connection/permission errors RE-THROW.
function isPgUndefinedFunctionError(error) {
  if (pgError.code === '42883') return true;
  // fallback across drivers: message contains 'pg_input_is_valid' AND
  // ('does not exist' | 'no such function' | 'undefined function')
}
// sqlIdentifiers — deterministic truncation keeps uniqueness
const suffix = `_${hashIdentifier(identifier)}`;      // FNV-1a → base36(7)
return `${identifier.slice(0, 63 - suffix.length)}${suffix}`;
```

**Flow:** runtime probes run once where needed; polyfill assert (`public.teable_try_cast_valid`) is side-effect-free — migrations own DDL, app only verifies callability. Identifier minting hashes ONLY when >63 chars so short names stay stable/readable.

**Invariants:**
1. Never infer capability from `version()` strings (pglite/cloud variants lie); probe behavior and match error codes with a message fallback for driver variance.
2. Truncation MUST include the hash suffix or two long names collide after clipping; slice length accounts for the suffix.
3. Schema splitting takes the FIRST dot only and refuses to re-split quoted literals.

**Probe:** `packages/v2/adapter-table-repository-postgres/src/utils/detectPgCapability.spec.ts` (error-classification matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "hasPgInputIsValid toPostgresIdentifierWithHash", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt execution-probing with strict error classification and hash-suffix truncation. Adapt the polyfill name to your migration set. Omit driver-specific fallbacks you don't ship.
