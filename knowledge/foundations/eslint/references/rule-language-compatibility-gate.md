<!-- capsule-v2 -->
# Rule language-compatibility gate — how does ESLint decide a rule does not support the file's language, and when?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How should a multi-language host gate rules by declared language support without breaking disabled rules or namespaced plugins?

## meta.languages match grammar + deferred aggregation
**Path/Symbol:** `lib/config/config.js:doesRuleSupportLanguage` (:250–299), `validateRulesConfig` collection + aggregate throw (:667–720, :754–765), `normalizeLanguageName` (:236–240), `splitPluginIdentifier` (:222–229).
**Signature:** `doesRuleSupportLanguage(ruleLangs: string[]|undefined, configLanguageName: string, validPluginNames: string[]): boolean`.
**Data Shape:** rule side `meta.languages: string[]` entries are "*", "plugin/*", or "plugin/lang". Config side is the normalized language name ("js/js"; "@/" alias rewrites to "js/"); validPluginNames = [configPluginName, plugin.meta.namespace?].

### Decisive source
```js
if (!ruleLangs) return true;              // absent = universal (backward compat)
for (const langEntry of ruleLangs) {
  if (langEntry === "*") return true;                       // any language
  const { pluginName: rulePluginPart, objectName: ruleLangPart } =
    splitPluginIdentifier(langEntry);                       // LAST slash for scoped ids
  if (ruleLangPart === "*") {
    if (validPluginNames.includes(rulePluginPart)) return true;  // "test/*" matches "test/lang"
  } else if (validPluginNames.includes(rulePluginPart) &&
             ruleLangPart === configLangPart) return true;       // name OR namespace alias
}
return false;
// validateRulesConfig: disabled rules bypass everything:
if (ruleOptions[0] === 0) continue;
...
unsupportedLanguageRules.push(ruleId);   // collected, not thrown inline
// after the loop — ONE error lists every offender:
error.messageTemplate = "rule-unsupported-language";
// 'Key "rules": The following rules do not support the language "js/js": - "rule-a" ...'
```

**Flow:** at Config construction (after severity normalization and option validation) each ENABLED rule's meta.languages is structure-checked (array of strings), matched against the config language through validPluginNames, and mismatches accumulate into a single aggregated TypeError carrying ruleIds in messageData. meta.languages itself must be an array of strings or construction throws per-rule.
**Invariant:** the gate runs at CONFIG time, never mid-lint, and NEVER fires for disabled rules (`[0]`/"off" skips schema, language match, everything) so users can park dead configs for other languages. Aggregation matters: throwing on first mismatch hides how many rules need fixing.
**Probe:** `tests/lib/config/config.js` (:1031–1058 mismatch throw; :1061–1091 aggregation of two offenders; :1093–1120 disabled-rule bypass; :1122–1149 "plugin/*" wildcard; :1151–1190 meta.namespace aliasing; :1192–1229 "@/js"→"js/js" message normalization). Executed at pin: --grep 'toJSON|validateRulesConfig' → 31 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "doesRuleSupportLanguage unsupported-language normalizeLanguageName splitPluginIdentifier", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config.doesRuleSupportLanguage" });
```

## Verdict
Adopt absent-means-universal, wildcard ladder, namespace aliasing, disabled-rule bypass, and single aggregated error. Adapt the plugin/name vocabulary to host registries; omit the "@/js" special case unless porting ESLint's built-in plugin aliasing too.
