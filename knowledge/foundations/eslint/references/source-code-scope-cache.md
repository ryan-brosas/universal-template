<!-- capsule-v2 -->
# SourceCode scope acquisition — which scope does `getScope(node)` return, and how is caching lifetime managed?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** A rule author asks for "the scope of this node" — what exactly comes back, and what does a porter cache wrongly?

## Parent-climbing acquire with per-node memo

**Path/Symbol:** `lib/languages/js/source-code/source-code.js:SourceCode.getScope` (:657-689), `SourceCode.getAncestors` (:711-723), constructor caches (:305-311).
**Signature:** `getScope(currentNode: Node): Scope`; `getAncestors(node: Node): Node[]`.
**Data Shape:** `this[caches] = new Map([["scopes", new WeakMap()], ["vars", new Map()], ["configNodes", void 0], ["isGlobalReference", new WeakMap()]])` — node-keyed caches are WeakMaps; the name-keyed vars cache is a strong Map; configNodes is lazy.

### Decisive source

```js
	getScope(currentNode) {
		if (!currentNode) {
			throw new TypeError("Missing required argument: node.");
		}

		// check cache first
		const cache = this[caches].get("scopes");
		const cachedScope = cache.get(currentNode);

		if (cachedScope) {
			return cachedScope;
		}

		// On Program node, get the outermost scope to avoid return Node.js special function scope or ES modules scope.
		const inner = currentNode.type !== "Program";

		for (let node = currentNode; node; node = node.parent) {
			const scope = this.scopeManager.acquire(node, inner);

			if (scope) {
				if (scope.type === "function-expression-name") {
					cache.set(currentNode, scope.childScopes[0]);
					return scope.childScopes[0];
				}

				cache.set(currentNode, scope);
				return scope;
			}
		}

		cache.set(currentNode, this.scopeManager.scopes[0]);
		return this.scopeManager.scopes[0];
	}
```

**Flow:** Missing-node TypeError → WeakMap hit returns instantly → otherwise climb `node.parent` until `scopeManager.acquire(node, inner)` yields a scope, where `inner` is false ONLY when starting from Program (deliberately skipping Node.js wrapper / ES-module scopes) → a `function-expression-name` scope hops to `childScopes[0]` → ultimate fallback `scopes[0]`. EVERY return path caches under the ORIGINAL node. `getAncestors(node)` is uncached and cheap: parent walk then `.reverse()` so index 0 is Program.
**Invariant:** The cached answer for a node never depends on who asked first beyond correctness (all paths yield the same scope for that node); weak caching means the whole map dies with the AST — porting these caches as strong Maps leaks memory across re-parses and risks stale hits if an instance outlives its tree.
**Probe:** `tests/lib/languages/js/source-code/source-code.js` `describe("getScope")` :1150+ (helper at :1179 builds SourceCode + asserts acquired scope types). Executed: `npx mocha tests/lib/languages/js/source-code/source-code.js --grep "getScope"` → 27 passing, exit 0.

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__get_code_snippet"]({ project: "eslint", qualified_name: "eslint.lib.languages.js.source-code.source-code.SourceCode.getScope" });
// → live source at :657-689 (executed)
```

## Verdict

Adopt parent-climbing acquire, the Program-only `inner=false` switch, the function-expression-name hop, and WeakMap-for-node-keys. Adapt scope-manager API to host. Omit the vars/configNodes caches unless you also port `markVariableAsUsed`/inline-config planes. Coverage note (pass-7 drift correction): `SourceCode.getCommentsBefore/After/Between` and `applyChanges` DO NOT EXIST at this pin — comment adjacency lives on TokenStore (see token-store-index-map), so any older design assuming them is stale.
