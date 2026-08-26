<!-- capsule-v2 -->
# Rules cross-config merge — how do two flat-config elements combine their `rules` objects, especially severity-only overrides?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** When element B re-declares a rule that element A configured with options, what survives?

## `rulesSchema.merge` algebra

**Path/Symbol:** `lib/config/flat-config-schema.js:rulesSchema.merge` (:454-509) with `normalizeRuleOptions` (:132-139) and eager-shape `rulesSchema.validate` (:510-532).
**Signature:** `merge(first?: object, second?: object): Record<string, RuleOptions[]>`.
**Data Shape:** Entries are severity-or-array forms (`"warn" | 2 | [severity, ...options]`). `normalizeRuleOptions` array-wraps non-arrays, maps `ruleSeverities` (`off/warn/error ⇄ 0/1/2`) onto index 0, and `structuredClone`s the result.

### Decisive source

```js
				/*
				 * If the second rule config only has a severity (length of 1),
				 * then use that severity and keep the rest of the options from
				 * the first rule config.
				 */
				if (secondRuleOptions.length === 1) {
					result[ruleId] = [
						secondRuleOptions[0],
						...firstRuleOptions.slice(1),
					];
					continue;
				}
```

**Flow:** Spread `{...first, ...second}` for the key universe; delete a literal `__proto__` key; every value is re-normalized through `normalizeRuleOptions` (so even single-parent entries come out as cloned `[number, ...options]` arrays); if both parents declare the rule and the SECOND entry is severity-only, splice the second severity onto the first parent's remaining options; otherwise the second entry wins whole. Per-key failures rethrow as `` Key "<ruleId>": <message> `` with `cause`.
**Invariant:** Merged rule options are FRESH objects (never aliased to either input — `structuredClone` guarantees it); a later severity-only tweak cannot silently drop an earlier element's options; `validate` deliberately defers per-rule schema validation to finalize() because the rule definition may not be resolvable while configs are still assembling.
**Probe:** `tests/lib/config/flat-config-schema.js` `describe("merge")` (24 passing, exit 0). Executed behavioral probe through the exported table: `merge({"a/b":[2,{x:1}], c:"warn"}, {"a/b":["warn"]})` → `a/b` = `[1,{"x":1}]` (second severity + first options), `c` = `[1]` (normalized); re-merging with a captured options object shows `result[ruleId][1] === opts` is `false` (no aliasing).

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__search_graph"]({ project: "eslint", qn_pattern: "^eslint\\.lib\\.config\\.flat-config-schema\\.", fields: ["lines"], limit: 40, format: "json" });
// → full member table incl. rulesSchema.merge at 454-509 (executed)
```

## Verdict

Adopt the three-way merge outcome table (absent-parent normalize / severity-only splice / second-wins) and clone-on-merge. Adapt severity vocabulary and error wrapping to host. Omit the ajv-free eager validation if your host resolves rules earlier. Distinct from `default-options-deep-merge` (rule-level positional defaults) — this seam composes CONFIG ELEMENTS.