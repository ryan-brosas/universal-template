<!-- capsule-v2 -->
# Feature Loader Lifecycle — how does an extension run hundreds of DOM-patching features safely across GitHub's SPA navigations?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How does one gate, (re)run, and tear down N independent DOM features on a soft-navigating SPA without leaks or stale listeners?

## Connected graph-selected seam
`feature-manager.add` is the graph's top fan-in node (183 inbound edges): every feature file calls it once at import time.

**Path/Symbol:** `source/feature-manager.tsx:` `add` (:157–239), `globalReady` (:74–151), `unloadAll` (:63–71), `unload` (:245–250); `source/helpers/map-of-arrays.ts:ArrayMap`.
**Signature:** `add(url: string, ...loaders: FeatureLoader[]): Promise<void>` where `FeatureLoader = RunConditions & { shortcuts?, awaitDomReady?, requiresToken?, deduplicate?(deprecated), init: Arrayable<(signal: AbortSignal) => Promisable<void | false>> }`.
**Data Shape:** `currentFeatureControllers: ArrayMap<FeatureId, AbortController[]>` — one controller PER RUN (a feature that ran 3 times holds 3 controllers). `globalReady: Promise<RghOptions>` resolved once after options + hotfixes + body-ready all settle.

### Decisive source
```ts
// Registration happens at import time; add() awaits the shared readiness promise:
const options = await globalReady;
if (isFeatureDisabled(options, id) && !isFeaturePrivate(id)) { /* mark rgh-OFF-<id>, return */ }
void asyncForEach(loaders, async loader => {
	if (include?.length === 0) throw new Error(`${id}: \`include\` cannot be an empty array, it means "run nowhere"`);
	let isFirstLoop = true;
	do {
		if (awaitDomReady) await domLoaded;
		// ...deduplicate check (deprecated), shouldFeatureRun, requiresToken...
		const featureController = new AbortController();
		currentFeatureControllers.append(id, featureController);
		// Do not await, or else an error on a page will break the feature completely until a reload
		void asyncForEach(castArray(init), async singleInit => {
			const didRun = await singleInit(featureController.signal);
			if (didRun !== false && !isFeaturePrivate(id)) {
				log.info('✅', id);
				for (const [hotkey, description] of Object.entries(shortcuts)) shortcutMap.set(hotkey, description);
			}
		});
	} while (await oneEvent(document, ['turbo:render', 'soft-nav:react-done']));
});
```

**Flow:** imports register features → each `add` awaits `globalReady` (options storage + contentScriptToggle + cached broken-features + bisect state, then `waitFor(() => document.body)`, double-load guard via `[refined-github]` attribute, `turbo:before-fetch-request`/`turbo:visit` → `unloadAll`) → disabled/private filtering → per loader a `do…while` loop that RE-RUNS `init` after every soft navigation event → each run gets a fresh AbortController appended to the registry → init receives the signal and must wire all listeners/observers to it → returning `false` from init means "decided not to run here" (no ✅ log, no shortcut registration).
**Invariant:** every side effect of a run must die when its AbortSignal fires — `unloadAll()` aborts ALL controllers on SPA navigation because GitHub restores old DOM on history navigation; never share one controller across runs (an aborted run's replacement needs a live signal). Init arrays are fired without awaiting so one feature's throw can't block others; errors surface through the global error handlers instead.
**Probe:** no unit test targets feature-manager directly (it needs a browser). Deterministic pins: the two unload events are named verbatim at :147–148; the empty-`include` throw at :198–199; the `didRun !== false` logging contract at :229–235. Recorded behavior tests live as "Test URLs" comments in every feature file (e.g. `source/features/batch-mark-files-as-viewed.tsx:118`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "feature-manager add unloadAll globalReady", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole pattern for any extension/userscript overlaying an SPA: import-time registration, single readiness promise, per-run AbortController registry, soft-nav re-run loop, `init returns false = skip`. Adapt the navigation event names (`turbo:render`, `soft-nav:react-done`) to your host's router events. Omit the deprecated `deduplicate` selector option (superseded by the caller-ID DOM marks, see caller-id-dedupe capsule) and GitHub-specific page detection. Coverage caveat: behavior is pinned by usage across 300 features + named events, not by a unit test.
