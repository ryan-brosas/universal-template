<!-- capsule-v2 -->
# preserve_identifier_case three-state — how did the pin commit turn a boolean setting into an enum without breaking 1.x configs?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5` (commit #24375 IS this change); Codebase Memory `ext-duckdb`. **Question:** How is `preserve_identifier_case = preserve_case|lowercase|uppercase` parsed with legacy boolean compatibility, and where does folding actually apply?

## Boolean cast first, enum second; NULL rejected; quoted identifiers always exact
**Path/Symbol:** setting struct `src/include/duckdb/main/settings.hpp:PreserveIdentifierCaseSetting` (:1731-1740); setter `src/main/settings/custom_settings.cpp:PreserveIdentifierCaseSetting::OnSet` (:1204-1226); enum `src/include/duckdb/common/enums/identifier_case_mode.hpp:16`; re-parse guard `src/main/client_verify.cpp:93`.
**Signature:** `static void OnSet(SettingCallbackInfo &, Value &input)`; RETURN_TYPE `IdentifierCaseMode`, DefaultValue `"preserve_case"`.
**Data Shape:** accepted spellings — enum names plus legacy booleans (`true/1/t/y/yes → preserve_case`, `false/0/f/n/no → lowercase`).

### Decisive source
```cpp
if (input.IsNull()) throw InvalidInputException("preserve_identifier_case setting cannot be NULL");
// backwards compatibility with the 1.x boolean setting: accept anything that casts to BOOLEAN,
// mapping true to preserve_case and false to lowercase
auto boolean_value = input.DefaultTryCastAs(LogicalType::BOOLEAN);
if (boolean_value) { input = Value(BooleanValue::Get(*boolean_value) ? "preserve_case" : "lowercase"); return; }
try { EnumUtil::FromString<IdentifierCaseMode>(parameter); }
catch (NotImplementedException &) {
    throw InvalidInputException("Unrecognized parameter for option preserve_identifier_case \"%s\", "
                                "expected one of: preserve_case, lowercase, uppercase", parameter);
}
```

**Flow:** SET → OnSet normalizes to a canonical string value → parser_options carry `identifier_case_mode` so unquoted identifiers fold at parse time; quoted identifiers bypass folding in every mode.
**Invariant:** ToString()-reparse verification must force PRESERVE_CASE ("folding them a second time would corrupt any identifier that was quoted in the original statement") — folding is a parse-time, one-way transform.
**Probe:** direct test `test/sql/settings/setting_preserve_identifier_case.test` pins all three modes; error arm at :115 regex-matches `Unrecognized parameter for option preserve_identifier_case \"bogus\"`. Probe: `grep -n 'input.DefaultTryCastAs(LogicalType::BOOLEAN)' src/main/settings/custom_settings.cpp` → :1210.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "PreserveIdentifierCaseSetting IdentifierCaseMode OnSet identifier_case_mode", limit: 10 });
```

## Verdict
Adopt cast-legacy-first then strict-enum parsing for renamed settings; adapt your config plumbing; omit the client_verify reparse special case if you have no statement round-trip checker.
