<!-- capsule-v2 -->
# Cycle-safe deepMerge — how does recursive config merging terminate on self- and cross-referencing objects?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** What stops `settings`/`languageOptions` deep-merging from looping forever on cyclic config objects?

## Memoized pair recursion

**Path/Symbol:** `lib/config/flat-config-schema.js:deepMerge` (:73-124); consumed by `deepObjectAssignSchema.merge` (:335-340, the `settings` schema).
**Signature:** `deepMerge(first: object, second: object, mergeMap = new Map()): object`.
**Data Shape:** `mergeMap` nests `Map<first, Map<second, result>>`; the pending result is registered BEFORE recursing, so any cycle re-enters a completed/pending memo entry instead of recursing again.

### Decisive source

```js
function deepMerge(first, second, mergeMap = new Map()) {
	let secondMergeMap = mergeMap.get(first);

	if (secondMergeMap) {
		const result = secondMergeMap.get(second);

		if (result) {
			// If this combination of first and second arguments has been already visited, return the previously created result.
			return result;
		}
	} else {
		secondMergeMap = new Map();
		mergeMap.set(first, secondMergeMap);
	}

	const result = {
		...first,
		...second,
	};

	delete result.__proto__; // don't merge own property "__proto__"

	// Store the pending result for this combination of first and second arguments.
	secondMergeMap.set(second, result);

	for (const key of Object.keys(second)) {
		if (
			key === "__proto__" ||
			!Object.prototype.propertyIsEnumerable.call(first, key)
		) {
			continue;
		}

		const firstValue = first[key];
		const secondValue = second[key];

		if (isNonArrayObject(firstValue) && isNonArrayObject(secondValue)) {
			result[key] = deepMerge(firstValue, secondValue, mergeMap);
		} else if (isUndefined(secondValue)) {
			result[key] = firstValue;
		}
	}

	return result;
}
```

**Flow:** Baseline spread lets second win everywhere; then, walking only keys SECOND declares that are OWN ENUMERABLE on first, recurse into non-array object pairs, and restore first's value where second carries explicit `undefined`. Arrays, primitives, nulls, and functions overwrite atomically.
**Invariant:** Cyclic (self-, cross-, overlapping-reference) inputs terminate and produce consistent results because `(first, second)` pairs memoize; the merged object's prototype is untouched (`delete result.__proto__` kills a literal own `__proto__` data key); inherited/non-enumerable properties never participate.
**Probe:** `tests/lib/config/flat-config-schema.js` — cycle suite at :240-334 ("merges objects with self-references", overlapping self-references, cross-references, overlapping cross-references, "produces the same results…") and the ownership suite at :127-230 ("does not change the prototype of a merged object", "does not merge the '__proto__' property" :136, "considers only own enumerable properties" :207). Executed behavioral probe: `settings.merge({arr:[1,2],keep:1},{arr:[9],keep:undefined})` → `{"arr":[9],"keep":1}` (array replaced atomically, `undefined` restored first's value).

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__get_code_snippet"]({ project: "eslint", qualified_name: "eslint.lib.config.flat-config-schema.deepMerge" });
// → live source at :73-124 (executed)
```

## Verdict

Adopt the pre-recursion pair memo and the undefined-restores-first rule verbatim; both are the non-obvious parts. Adapt the ownership policy (ESLint treats config objects as disposable). Omit the `__proto__` deletions only if your runtime freezes Object.prototype — otherwise keep them.