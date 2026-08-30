<!-- capsule-v2 -->
# IEEE wire contract — how do non-finite values survive JSON serialization, filters, CSV export, and OpenAPI?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** JSON.stringify collapses Infinity/-Infinity/NaN to null — how does a pg numeric-formula cell reach clients distinguishably?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb-sdk/src/lib/formula/non-finite.ts` (whole, 26L) · `helpers/formulaNonFinite.ts:mapNonFiniteToString` (whole, 9L) · `db/BaseModelSqlv2.ts:convertFormulaNonFinite` (:8512–:8541; execAndParse hook :7368–:7372; option :200) · SDK `FormulaHelper.parsePlainCellValue` (:62–:65) · swaggerV2 `getSwaggerColumnMetas.ts` (:67–:78, interface :280–:281).
**Signature:** `mapNonFiniteToString(value: unknown): unknown` — number∧!finite → 'NaN'|'Infinity'|'-Infinity'; `isFormulaNonFiniteValue(v): v is FormulaNonFiniteValue`.
**Data Shape:** wire tokens are STRINGS `'Infinity' | '-Infinity' | 'NaN'`; conversion keyed by `getAs(col)` (= asId || id), not raw column id.

### Decisive source
```ts
// PG returns float8 Infinity/-Infinity/NaN as JS numbers, but JSON.stringify
// collapses all three to null — indistinguishable from a real NULL. Convert to
// strings before serialization. Display path only; sort/filter/aggregation use
// the NULLIF form where these never occur.
// The select is aliased with getAs (asId || id), not the raw id.
const key = getAs(col);
if (key in d) d[key] = mapNonFiniteToString(d[key]);
```

**Flow:** pg returns float8 specials as JS numbers → execAndParse runs convertFormulaNonFinite after date conversion, before user conversion (skippable via skipFormulaNonFiniteConversion) → cells carry string tokens → UI round-trips them as filter values (verify admits, binds ::double precision) → parsePlainCellValue passes tokens through untouched (the display parser would mangle them; governs CSV export too) → swagger declares pg numeric formulas as `oneOf: [{type:'number'},{type:'string'}]` + `nullable:true` (OpenAPI 3.0 has no type arrays).
**Invariant:** (1) Tokens exist BECAUSE JSON cannot represent the numbers — they are the wire format, not display sugar. (2) Conversion is pg-only and display-path-only: sort/filter/aggregation consume raw SQL where the NULLIF/exclusion forms already prevent or preserve specials. (3) Keying by getAs is load-bearing — select aliases use asId||id, so keying by column.id silently misses aliased columns. (4) Round-trip closure: UI can filter back on exactly the tokens the API emits.
**Probe:** `grep -c "Infinity" packages/nocodb-sdk/src/lib/formula/non-finite.ts` → 3 token set verbatim; `sed -n '7368,7372p' …BaseModelSqlv2.ts` hook position verified. No upstream unit suite for server path (SDK serializer specs cover the sign plane only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "convertFormulaNonFinite mapNonFiniteToString FORMULA_NON_FINITE_VALUES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the string-token wire contract + getAs keying + pass-through display parsing; adapt token spellings; omit swagger oneOf if your host predates OpenAPI 3. Caveat: server-side conversion untested upstream.
