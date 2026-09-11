<!-- capsule-v2 -->
# fixTypes filter composition — how do `fix` and `fixTypes` combine into one fixer predicate, and which messages can never be fixed under a fixTypes regime?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must know exactly which messages a fixTypes-filtered fixer touches, and why the constructor default for `fixTypes` is `null` rather than an array.

## Predicate-composing fixer factory

**Path/Symbol:** `lib/eslint/eslint-helpers.js:getFixerForFixTypes` (:1106-1116), `shouldMessageBeFixed` (:1089-1097); consumed at `lib/eslint/eslint.js:1184` (lintText) and `lib/eslint/eslint-helpers.js:1262` (lintFile).
**Signature:** `getFixerForFixTypes(fix: boolean | Function, fixTypesSet: Set<string> | null, config: CalculatedConfig): boolean | Function`.
**Data Shape:** `fixTypesSet` is built once per call site as `fixTypes ? new Set(fixTypes) : null`. Returns the ORIGINAL `fix` untouched unless BOTH `fix` and `fixTypesSet` are truthy. A boolean `true` becomes `() => true`; a function is kept as-is and AND-ed in.

### Decisive source

```js
function shouldMessageBeFixed(message, config, fixTypes) {
	if (!message.ruleId) {
		return fixTypes.has("directive");
	}

	const rule = message.ruleId && config.getRuleDefinition(message.ruleId);

	return Boolean(rule && rule.meta && fixTypes.has(rule.meta.type));
}
```

```js
	const originalFix = typeof fix === "function" ? fix : () => true;

	return message =>
		shouldMessageBeFixed(message, config, fixTypesSet) &&
		originalFix(message);
```

**Flow:** When both gates are truthy, the composed fixer runs `shouldMessageBeFixed` first, then the original predicate. ruleId-less messages (directive comments such as `// eslint-disable-line`) count as type `"directive"` — fixed iff `"directive"` ∈ the set. Rules whose definition or `meta` is missing, or whose `meta.type` is absent, resolve `fixTypes.has(undefined)` ⇒ `false` — such messages are REPORTED but NEVER fixed while fixTypes is active. This is why `processOptions` defaults `fixTypes` to `null` with the inline comment "should be null by default because if it's an array then it suppresses rules that don't have the `meta.type` property" (eslint-helpers.js :777-778).
**Invariant:** `fix: false` or `fixTypes: null` must leave the fixer byte-identical to the original option; the composition must AND (never OR) the type filter with the user predicate; a meta.type-less rule must never be silently fixed under an active fixTypes set.
**Probe:** `tests/lib/eslint/eslint.js` "Fix Types" describe (:9463+; validation throw for `["layou"]`, per-type fixture files for layout/suggestion/both, and the `fixTypes` without `fix` no-op case). Executed: `npx mocha tests/lib/eslint/eslint.js --grep "Fix Types"` (within the 20-passing subset). Executed live probe: under `fixTypes:["layout"]` a directive message is reported severity 1 and RETAINS its `.fix` property (reported-but-unfixed); adding `"directive"` to the set removes it via its own fix (messages `[]`, `output` present).

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getFixerForFixTypes shouldMessageBeFixed fixTypes directive", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint-helpers.js :1089-1116 (direct-read confirmed at pin)
```

## Verdict

Adopt the two-gate early return and the AND-composition; adopt the "directive" pseudo-type for ruleId-less messages. Adapt the config lookup (`config.getRuleDefinition`) to your host's rule registry. Omit nothing behavioral — but note the subtle reporting nuance: an unfixed-by-filter message still carries its `.fix` in the report; filtering happens at fixer-application time, not report time.
