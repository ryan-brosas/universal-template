<!-- capsule-v2 -->
# CLI option translation ladder — how do optionator flags become ESLint constructor options without changing semantics?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** Where does each CLI flag land in the programmatic options object, and which couplings are load-bearing?

## Pure async projection onto ESLint constructor options

**Path/Symbol:** `lib/shared/translate-cli-options.js:translateOptions` (:89-221; `module.exports = translateOptions` :223) with helpers `loadPlugins` (:36-57), `quietFixPredicate` (:66-68), `quietRuleFilter` (:76-78); flag defaults in `lib/options.js` (`config-lookup`, Boolean, default true).
**Signature:** `async translateOptions(cliOptions: ParsedCLIOptions): Promise<ESLintOptions>`.
**Data Shape:** Emits `overrideConfig` as an ARRAY: element 0 carries `languageOptions` (only when non-empty) + `rules` (+ optional `linterOptions`); an extra element carries `files` globs derived from `--ext`.

### Decisive source

```js
	let overrideConfigFile =
		typeof config === "string" ? config : !configLookup;
	if (overrideConfigFile === false) {
		overrideConfigFile = void 0;
	}
// ...
	const ruleFilter =
		quiet && maxWarnings === -1 ? quietRuleFilter : () => true;
// ...
		fix: (fix || fixDryRun) && (quiet ? quietFixPredicate : true),
```

**Flow:** Explicit `--config` wins as a path string; otherwise `!configLookup`: with optionator's default `--config-lookup true` this becomes false→void 0 (normal eslint.config.* discovery), while `--no-config-lookup` becomes true (skip lookup entirely). Globals parse NAME:true → writable else readonly; `--parser/--parser-options` fold into languageOptions. Quiet mode couples TWO predicates: warn-severity rules are FILTERED FROM EXECUTION only while maxWarnings === -1 (warns must still run to count against a real maxWarnings budget), and fixes apply only to severity-2 messages. `reportUnusedDisableDirectives` boolean maps to linterOptions STRING severity "error"/absent, while `--report-unused-disable-directives-severity` normalizes via normalizeSeverityToString. Plugins import in parallel, REQUIRE a default export, and register under the shorthand name. `--ext ts,.jsx` becomes files globs `**/*.ts`,`**/*.jsx` (leading dot added when missing).
**Invariant:** The function is a PURE projection — no filesystem access except dynamic plugin imports; severity PLANES differ deliberately here (CLI writes string severities into linterOptions while the schema layer normalizes reportUnusedInlineConfigs to a NUMBER); dropping the maxWarnings coupling silently breaks --max-warnings accounting.
**Probe:** No dedicated upstream test file exists (`tests/lib/shared/translate-cli-options.js` absent — recorded caveat). Executed behavioral probe (node -e, every output matched the source claims): extGlobs ["**/*.ts","**/*.jsx"]; globals {A:"writable",B:"readonly"}; warnFilter false,true; overrideConfigFile path-string,true,true,undefined for (config-string / bare call / --no-config-lookup / default-lookup); linterOptions reportUnusedDisableDirectives "error" then "warn"; quietFixPredicate function,false,true. Graph retrieval: search_graph name_pattern translateOptions|RuntimeInfo located the Function at :89-221 (executed).

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__get_code_snippet"]({ project: "eslint", qualified_name: "eslint.lib.shared.translate-cli-options.translateOptions" });
// → live source at :89-221 (executed)
```

## Verdict

Adopt the tri-state overrideConfigFile algebra, the quiet/maxWarnings coupling, and the two-predicate fix policy. Adapt option names and importer mechanics to host. Omit the ModuleImporter default-export gate only if your plugin loader already enforces it. Caveat: probe-based verification only — upstream has no direct suite for this module.
