<!-- capsule-v2 -->
# Default-config lazy proxy — how the built-in rule registry reaches every flat config without eager-loading 270 rules

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0; direct source+test fallback — Codebase Memory MCP not connected this session). **Question:** How does the flat-config engine give every file access to all built-in rules while keeping rule modules unloaded until a config actually names one?

## defaultConfig / defaultRuleTesterConfig
**Path/Symbol:** `lib/config/default-config.js:defaultConfig` (:22-60), `defaultRuleTesterConfig` (:62-66), module-level `sharedDefaultConfig` (:17-20); the rules proxy (:32-45); consumer `lib/eslint/eslint-helpers.js:createDefaultConfigs` (:1354-1367) + `createConfigLoader` (defaultConfigs appended per config file, config-loader.js :637).
**Signature:** `exports.defaultConfig = Object.freeze([pluginEntry, ignoresEntry, ...sharedDefaultConfig])`; `exports.defaultRuleTesterConfig = Object.freeze([{ files: ["**"] }, ...sharedDefaultConfig])`.
**Data Shape:** 4 frozen elements: (0) `{ plugins: { "@": { languages: { js }, rules: Proxy } }, language: "@/js", linterOptions: { reportUnusedDisableDirectives: 1 } }`; (1) `{ ignores: ["**/node_modules/", ".git/"] }`; (2) `{ files: ["**/*.js", "**/*.mjs"] }`; (3) `{ files: ["**/*.cjs"], languageOptions: { sourceType: "commonjs", ecmaVersion: "latest" } }`.

### Decisive source

```js
rules: new Proxy(
	{},
	{
		get(target, property) {
			return Rules.get(property);
		},

		has(target, property) {
			return Rules.has(property);
		},
	},
),
```

```js
const sharedDefaultConfig = [
	// intentionally empty config to ensure these files are globbed by default
	{ files: ["**/*.js", "**/*.mjs"] },
	{ files: ["**/*.cjs"], languageOptions: { sourceType: "commonjs", ecmaVersion: "latest" } },
];
```

**Flow:** `Rules` is the LazyLoadingRuleMap of ~270 built-in rules; the proxy forwards `get`/`has` into it so a config that never mentions a rule never loads its module — the comment in-source says exactly this ("try to delay loading rules until absolutely necessary"). The proxy is the `"@"` plugin's rules surface, so built-ins resolve under the `@/` namespace (`language: "@/js"`). The ignores entry makes the engine ignore node_modules/.git by default; the glob entries ensure .js/.mjs/.cjs files are linted WITHOUT any user config. `createDefaultConfigs(optionPlugins)` adds a separate `{plugins}` shard (shorthand names via getShorthandName) for CLI `--plugin` options, appended after the config-file configs. The RuleTester variant replaces the plugin/glob entries with `{files:["**"]}` and shares the two glob entries BY REFERENCE — tester cases match every file without inheriting default ignores.
**Invariant:** the default array is frozen (no mutation of shared config state); rule loading stays lazy THROUGH the config layer (proxy get-trap, not eager spread); the get-trap SHADOWS Map method names — `rulesProxy.has`/`rulesProxy.get` are `undefined` because `Rules.get("has")` is undefined; only ruleId reads (`rules["no-var"]`) and `in` checks work. The tester config must NOT carry the default ignores (tests lint fixture paths under node_modules-like dirs).
**Probe:** NO dedicated suite (`tests/lib/config/default-config.js` ABSENT — coverage caveat; behavior pinned via tester/linter integration and live probes). Executed live: `Object.isFrozen(defaultConfig)` true, length 4; `rulesProxy["no-var"]` returns a module with `create()`; `rulesProxy["not-a-rule-xyz"]` undefined; `"no-var" in rulesProxy` true / unknown false; `rulesProxy.has` undefined (shadowing confirmed); tester entries 1-2 are the SAME objects as defaultConfig entries 2-3 (reference equality).

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "defaultConfig sharedDefaultConfig rules Proxy Rules.get", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/config/default-config.js :17-66 (direct-read confirmed at pin)
```

## Verdict

Adopt the proxy-bridged lazy registry inside a frozen default config array and the reference-shared tester variant; adapt the default glob/sourceType entries and ignore list to host language support. Omit the `"@"` namespace indirection only if your host has no plugin namespace concept. Critical porting note: any code path that treats the rules surface as a Map (calls .get/.has/.entries on it) breaks — expose iteration through the underlying LazyLoadingRuleMap, never through the proxy.
