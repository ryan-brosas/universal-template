<!-- capsule-v2 -->
# Checkbox/numeric op overrides — how do checked/notchecked fold NULL, why does rating's lt include NULL, and which dialects need 0/1 read repair?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What are the exact clause shapes for checkbox/rating/duration/year/currency/colour value families, and where does the numeric inheritance chain bend them?

## Checkbox + Rating + Duration/Year/Currency parse chains
**Path/Symbol:** `checkbox/checkbox.general.handler.ts` — filterChecked :23-39; filterNotchecked :41-59 (NULL ∪ false); verifyFilter value table :61-123. `rating/rating.general.handler.ts` — filterLt/Lte/Gte NULL arms :36-93. `duration/duration.general.handler.ts` (string "00:02:33.000"→seconds ladder, negative rejection). `year/year.general.handler.ts` (:20-35 range 1000-9999). `currency/currency.general.handler.ts` getNumericValue(locale) :17-33. `checkbox.sqlite.handler.ts` parseDbValue 1↔true / 0↔false.
**Signature:** `RatingGeneralHandler extends DecimalGeneralHandler extends GenericFieldHandler`; `NumberGeneralHandler extends DecimalGeneralHandler` adding integer-only rejection (`Math.floor !== Math.ceil → invalid`).
**Data Shape:** Checkbox verify accepts `[null,true,false,'true','false','',1,0,'1','0']`; rating bounds from `parseProp(column.meta).max`.

### Decisive source
```ts
// checkbox.general.handler.ts :32-38:
// Checkbox columns store NULL for "never set" and false for "explicitly
// unchecked"; both should match `notchecked`.
grpdQb.whereNull(sourceField).orWhere(sourceField, this.notcheckedDbValue);
// rating.general.handler.ts :44-50 — un-rated rows satisfy low thresholds:
qb.where(sourceField, '<', val);
if (val > 0) qb.orWhereNull(sourceField);      // lte: val >= 0; gte: val <= 0
```

**Flow:** checked = `= true-value` (dialect getter; sqlite repairs stored 1/0 on READ via parseDbValue); notchecked folds NULL+false. Rating's comparison trio adds orWhereNull asymmetrically so zero-valued filters don't exclude never-rated rows while positive thresholds do. Duration converts duration-strings via convertDurationToSeconds(type) else Number, rejects negatives. Year rejects outside 1000..9999. Currency parses locale-formatted strings through SDK getNumericValue. Colour normalizes hex (#RRGGBB uppercase or reject).
**Invariant:** (1) The rating NULL-arm thresholds mirror at 0: `lt: val>0`, `lte: val>=0`, `gte: val<=0` — gt gets NO arm (NULL is never > anything semantically wanted). (2) SQLite boolean repair is READ-side only; writes keep engine-native ints. (3) Numeric family shares DecimalGeneralHandler's blank/notblank/neq overrides (strict-NULL forms) via method-delegation shells in decimal.pg/mysql/sqlite handlers — the dialect class inherits PG ilike behavior WHILE borrowing general's filter table through instance delegation (`override filter = this.decimalGeneralHandler.filter`).
**Probe:** No unit tests upstream at pin. Deterministic probe: grep '"never set" and false' (:39); search_graph resolves `RatingGeneralHandler.filterLt Method ... :36-54` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DecimalPgHandler", limit: 5 });
```

## Verdict
Adopt the NULL-folding tables and delegation-shell pattern for dialect reuse; adapt value getters per storage; omit empty dialect subclasses (CheckboxMssql etc.). Caveat: no direct tests at pin.
