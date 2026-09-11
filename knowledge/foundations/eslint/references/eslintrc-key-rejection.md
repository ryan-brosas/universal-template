<!-- capsule-v2 -->
# Eslintrc trap keys — how does a flat config fail fast on eslintrc-era keys with actionable errors?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** Which top-level keys must always throw in flat config, and what error shape should they produce?

## Always-throw schemas over the trap-key table

**Path/Symbol:** `lib/config/flat-config-schema.js:createEslintrcErrorSchema` (:545-552), `eslintrcKeys` (:554-565), `flatConfigSchema` table (:571-591), `IncompatibleKeyError` (:256-267), `IncompatiblePluginsError` (:272-284).
**Signature:** `createEslintrcErrorSchema(key: string): { merge: "replace", validate(): never }`.
**Data Shape:** Errors carry `messageTemplate` ("eslintrc-incompat" / "eslintrc-plugins") plus `messageData`, so tooling can match on the template rather than prose.

### Decisive source

```js
function createEslintrcErrorSchema(key) {
	return {
		merge: "replace",
		validate() {
			throw new IncompatibleKeyError(key);
		},
	};
}

const eslintrcKeys = [
	"env",
	"extends",
	"globals",
	"ignorePatterns",
	"noInlineConfig",
	"overrides",
	"parser",
	"parserOptions",
	"reportUnusedDisableDirectives",
	"root",
];

const flatConfigSchema = {
	// eslintrc-style keys that should always error
	...Object.fromEntries(
		eslintrcKeys.map(key => [key, createEslintrcErrorSchema(key)]),
	),
	// ... flat config keys follow
};
```

**Flow:** The full schema is composed by spreading generated always-throw entries UNDER the real flat-config keys; any config object carrying a trap key fails at validate time with one stable message ("This appears to be in eslintrc format rather than flat config format."). `plugins.validate` has its own eslintrc special case: an ARRAY of strings throws `IncompatiblePluginsError` ("array of strings rather than flat config format (object)").
**Invariant:** The trap list is exact and includes keys that are legal elsewhere: `globals`, `parser`, `parserOptions`, and `reportUnusedDisableDirectives` are INVALID at flat-config TOP level because they belong under `languageOptions` / `linterOptions`. Validation errors are machine-classifiable via messageTemplate + messageData.
**Probe:** Executed behavioral probe through the exported table: `flatConfigSchema.env.validate({browser:true})` threw with `messageTemplate=eslintrc-incompat | This appears to be in eslintrc format rather than flat config format.`; `plugins.merge({p:{x:1}},{p:{y:2}})` threw `Cannot redefine plugin "p".` Direct suite: `npx mocha tests/lib/config/flat-config-schema.js` → 24 passing.

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__search_graph"]({ project: "eslint", name_pattern: "flatConfigSchema|IncompatibleKeyError", limit: 10, fields: ["lines"], format: "json" });
// → flatConfigSchema variable at lib/config/flat-config-schema.js 571-591 + test file node (executed)
```

## Verdict

Adopt the generated-trap-schema pattern and the template+data error shape. Adapt the key list to whichever legacy dialect your host must reject. Omit nothing from the list without checking your host's migration docs — dropping e.g. `globals` silently accepts configs that mean something different under flat semantics.
