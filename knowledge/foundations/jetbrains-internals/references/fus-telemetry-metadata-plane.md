<!-- capsule-v2 -->
# FUS telemetry metadata plane — how is analytics instrumented as data (dictionaries, whitelists, group schemas)?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does a product ship telemetry WITHOUT leaking free-form user strings — what dictionaries/whitelists/schema files make events privacy-bounded by construction?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.pycharm.pro.jar:event-log-metadata/FUS/dictionaries/*` (8 dicts + `dictionaries.json` registry) and `lib/intellij.platform.statistics.jar:statistics/{actionsUsagesV3.csv,actionsUsagesV4.csv,contributorsSelections.csv}`.
**Signature:** `dictionaries.json` = `{"dictionaries":["composer_packages.ndjson","crate_names.ndjson","dotnet_technologies.ndjson","grazie_rule_ids.ndjson",…]}`; each dict has an integer `.meta` sidecar (epoch build stamp, e.g. 1765562765).
**Data Shape:** `.ndjson` dictionary = one whitelisted identifier per line (npm package names, crate names, tech names) — event payloads may only emit values PRESENT in a dictionary. CSVs = aggregated usage priors: `WelcomeScreen.Plugins,,PLATFORM,965,1670,179693` → actionId,pluginId?,scope,count,total,buildStamp.

### Decisive source
```
event-log-metadata/FUS/dictionaries/dictionaries.json
→ {"dictionaries" : [ "composer_packages.ndjson", "crate_names.ndjson",
   "dotnet_technologies.ndjson", "grazie_rule_ids.ndjson",
   "grazie_rule_long_ids.ndjson", "ktor_feature_ids.ndjson",
   "look_and_feel.ndjson", "python_packages.ndjson" ]}
statistics/actionsUsagesV3.csv
→ Git.Fetch,Git4Idea,JB_BUNDLED,259,1197,179693
```

**Flow:** instrumentation declares a counter collector (see `<statistics.counterUsagesCollector …/>` in mcpserver plugin.xml) → validation rule constrains string fields to a shipped dictionary (`<statistics.validation.customValidationRule implementation="…McpToolNameValidator"/>` pairs with the tool-name allowlist concept) → out-of-dictionary values are dropped/anonymized at emission.
**Invariant:** the dictionary file IS the privacy boundary: telemetry can never enumerate unlisted identifiers, so the ndjson corpus must be curated per ecosystem. Meta stamps let the server know which whitelist version produced an event.
**Probe:** `unzip -p lib/intellij.pycharm.pro.jar event-log-metadata/FUS/dictionaries/dictionaries.json` → 8 entries; `unzip -p lib/intellij.platform.statistics.jar statistics/actionsUsagesV3.csv | head -1`.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "counter usages collector statistics validation", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dictionary-whitelisted string telemetry, per-ecosystem ndjson vocabularies with meta-stamped versions, shipped usage-prior CSVs for bootstrapping ranking heuristics offline. Adapt schema to your pipeline. Omit actual whitelists if your jurisdiction differs. Complements pass-2's code-provenance capsule on the AI-telemetry side.
