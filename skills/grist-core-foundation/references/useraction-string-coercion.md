<!-- capsule-v2 -->
# User-action string coercion — where do API-supplied strings get typed BEFORE the data engine sees them?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Which user actions have their col_values parsed, at which array positions, and when is parsing skipped entirely?

## parseUserAction dispatches by action name and position; unknown table/column ⇒ values pass through untouched
**Path/Symbol:** `app/common/ValueParser.ts`: `parseUserAction` (:341–364), `_parseUserActionColValues` (:367–377), `parseColValues` (:300–339) — table lookup miss :305–308, column miss :312–314, IdentityParser short-circuit :320–322.
**Signature:** `parseUserAction(ua: UserAction, docData: DocData): UserAction` (copy; original untouched).
**Data Shape:** Positions: default LAST element; `AddOrUpdateRecord`/`BulkAddOrUpdateRecord` parse BOTH index 2 (`require`) and 3 (`col_values`).

### Decisive source
```ts
switch (ua[0]) {
  case "AddRecord": case "UpdateRecord":
    return _parseUserActionColValues(ua, docData, false);
  case "BulkAddRecord": case "BulkUpdateRecord": case "ReplaceTableData":
    return _parseUserActionColValues(ua, docData, true);
  case "AddOrUpdateRecord":
    ua = _parseUserActionColValues(ua, docData, false, 2);   // require
    ua = _parseUserActionColValues(ua, docData, false, 3);   // col_values ('fields' in the API)
    return ua;
  case "BulkAddOrUpdateRecord":
    ua = _parseUserActionColValues(ua, docData, true, 2);
    ua = _parseUserActionColValues(ua, docData, true, 3);
    return ua;
  default: return ua;
}
...
// parseColValues internals
const tableRef = tablesTable.findRow("tableId", tableId);
if (!tableRef) { return colValues; }                    // unknown table: let something else error
const parser = createParser(docData, colRef);
if (parser instanceof IdentityParser) { return values; }// no coercion for Text etc.
```

**Flow:** action-name switch → per-column parser built from live metadata (`createParser` reads `_grist_Tables_column` + view-field overrides where field widgetOptions exist) → only STRING members parsed (`typeof val === "string"` guard) → non-existent table/column or identity-parser types return values verbatim.
**Invariant:** Parsing is metadata-driven and FAILS OPEN to the engine: missing metadata never fabricates a value. Only strings are touched — a caller who already sent numbers is respected. The field-overrides-column rule (`field?.widgetOptions ? field : col`, :270) mirrors how FORMATTING picks options, keeping paste and display consistent. A porter applying this at the wrong layer (inside the engine) double-parses; it belongs at the client-facing boundary.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "case \"AddOrUpdateRecord\"" app/common/ValueParser.ts && grep -n "parser instanceof IdentityParser" app/common/ValueParser.ts && grep -rln "parseUserAction" app/server --include=*.ts'` → :350, :320, and the server entry point(s) consuming it.
Direct tests: exercised through ActiveDoc apply-path suites (`grep -rln "parseUserAction" test/server`).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseUserAction BulkAddOrUpdateRecord AddOrUpdateRecord colValues","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the boundary placement + fail-open misses + string-only rule; adapt the action-name set to your protocol; omit position-2 handling if your upsert variant lacks a `require` clause.
