<!-- capsule-v2 -->
# Config↔code linking — how do you connect a YAML key or package.json dependency to the code that uses it?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What three strategies, confidences, and false-positive guards link config files to symbols?

## Key→Symbol / Dep→Import / File→Ref with graded confidence
**Path/Symbol:** `src/pipeline/pass_configlink.c` (header 1–34, confidences 27–34) + tests/test_configlink.c:89–230.
**Signature:** (predump pass) emits CONFIGURES/DEPENDS_ON edges into the graph buffer before dump.
**Data Shape:** Confidence scores: KEY_EXACT 0.85, KEY_SUBSTRING 0.75, DEP_EXACT 0.95, DEP_QN_SUBSTR 0.80, FILE_FULLPATH 0.90, FILE_BASENAME 0.70. Short keys are SKIPPED (< threshold length) to kill noise; camelCase keys normalize for matching; substring matches must not fire on unrelated symbols.

### Decisive source
```c
/* Three strategies link config files to code symbols:
 *   1. Key→Symbol: normalized config key matches code function/variable name
 *   2. Dep→Import: package manifest dependency matches IMPORTS edge target
 *   3. File→Ref: source code string literal references config file path */
TEST(configlink_key_symbol_short_key_skipped) { ... }
TEST(configlink_key_symbol_no_false_positive) { ... }
```

**Flow:** walk config values → strategy 1: normalize key (`maxConnections`→`max connections` tokens), exact-then-substring match against symbol names with short-key veto → strategy 2: manifest deps matched against IMPORTS targets (exact then QN-substring) → strategy 3: string literals referencing config paths (full path beats basename) → emit typed edges carrying the strategy confidence.
**Invariant:** Substring strategies must be strictly weaker than exact ones AND carry explicit negative guards — config keys like "port" would otherwise link to every symbol containing port.
**Probe:** `tests/test_configlink.c:configlink_key_symbol_exact_match`, `configlink_key_symbol_substring_match`, `configlink_key_symbol_short_key_skipped`, `configlink_key_symbol_camel_case`, `configlink_dep_import_package_json`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_pipeline_pass_configlink", limit: 5 });
```

## Verdict
Adopt graded-strategy linking with per-strategy negative guards; adapt normalization to your config dialects; omit INFRA_MAPS if you don't index deploy files.
