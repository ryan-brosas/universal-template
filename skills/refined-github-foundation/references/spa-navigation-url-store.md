<!-- capsule-v2 -->
# spa-navigation-url-store — how do you give Svelte components a live SPA URL that survives soft navigation?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** A Svelte component needs to react to the current URL across soft navigations (the SPA never reloads, so `location.href` read once at mount is stale after the first navigation). How do you expose the live URL as a reactive store without each component wiring its own listeners?

## Readable store seeded, immediately refreshed, and bound to the host navigation event
**Path/Symbol:** `source/components/url.ts` — `stripHash` :4–8, `urlStore` :10–24.
**Signature:** `urlStore: Readable<string>` (default export); `stripHash(url: string): string` (module-local).
**Data Shape:** current page URL as a string with the hash fragment removed; query parameters preserved.

### Decisive source
```ts
// Do not replace with `getCleanPathname`, we read the URL parameters too
function stripHash(url: string): string {
	const u = new URL(url);
	u.hash = '';
	return u.href;
}

const urlStore = readable(stripHash(location.href), set => {
	// The first value might be set before any subscribers appear.
	// The first subscriber will then call this function, but receive the cached value instead of the real URL.
	// This updates the value immediately.
	set(stripHash(location.href));

	const handler = (event: NavigateEvent): void => {
		set(stripHash(event.destination.url));
	};

	navigation.addEventListener('navigate', handler);
	return () => {
		navigation.removeEventListener('navigate', handler);
	};
});
```

**Flow:** the store is seeded with `stripHash(location.href)` at module load → inside the subscribe callback, the CURRENT url is re-set BEFORE registering the listener (the three-line comment documents why: the seed may have been computed long before the first subscriber exists, so without this the first subscriber would receive a stale URL) → every host 'navigate' event pushes `event.destination.url` through the same strip → unsubscribe removes exactly the listener it added.
**Invariant:** (1) the immediate re-set in subscribe is the load-bearing line — Svelte's `readable` calls the start function per subscriber with the CACHED initial value, so any store seeded at module scope over a mutable source needs this refresh-on-subscribe pattern; (2) hash-only stripping is deliberate ("we read the URL parameters too") — a port that also drops the query string breaks consumers reading `searchParams`; (3) the event source is the host's Turbo `navigation` GLOBAL — it is NOT declared in globals.d.ts and url.ts is its only usage site in the repo, so this store is a hard dependency on the host exposing the Navigation API object (adapt to your host's navigation event surface); (4) one listener per subscriber, removed on unsubscribe — no global listener leak across component lifetimes.
**Probe:** executed pins: `grep -n "Do not replace with" source/components/url.ts` → line 3; `grep -n "The first value might be set" source/components/url.ts` → line 11; `grep -n "navigation.addEventListener" source/components/url.ts` → line 20. No direct unit test upstream (browser-bound). COVERAGE CAVEAT: `urlStore` itself has no graph node (module-level const — search_graph resolves only `stripHash` :4–8); cited from direct source read.

## Consumer: derived feature identity from the live URL
**Path/Symbol:** `source/features/rgh-feature-descriptions.svelte` — `idFromUrl` :19–29, `pathname` :44–48.
**Signature:** Svelte 5 `$derived.by` blocks over `$urlStore`.

### Decisive source
```svelte
const idFromUrl = $derived.by(() => {
	if (isReportingBug) {
		const title = new URL($urlStore).searchParams.get('title') ?? '';
		return /^`(?<id>[^`]+)`/.exec(title)?.groups?.id ?? undefined;
	}

	return /\/(?<id>[^/]+)\.(?:tsx|css)$/.exec(new URL($urlStore).pathname)
		?.groups?.id ?? undefined;
}) as FeatureId | undefined;
```

**Flow:** the feature-description panel derives WHICH feature the user is looking at from the live URL — two grammars: on a new-issue page the id comes from the backtick-quoted issue TITLE (`searchParams.get('title')`), elsewhere from the file PATHNAME (`/features/<id>.tsx|.css`) → downstream `$derived`s (meta lookup, rename mapping via `getNewFeatureName`, css/tsx twin links) all recompute automatically on every soft navigation because they read `$urlStore`.
**Invariant:** the dual-grammar split (query-param id vs pathname id) is keyed on PAGE TYPE (`pageDetect.isNewIssue()`), not on URL shape sniffing — a port should branch on an explicit route predicate; the store itself stays grammar-agnostic (it carries the raw URL, consumers parse).
**Probe:** executed pins: `grep -n "import urlStore" source/features/rgh-feature-descriptions.svelte` → line 8; `grep -n "idFromUrl = \$derived.by" source/features/rgh-feature-descriptions.svelte` → line 19; `grep -n '\$urlStore' source/features/rgh-feature-descriptions.svelte` → lines 21, 25, 46. Single consumer repo-wide (grep-verified).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "urlStore stripHash" });
// total: 1 — refined-github.source.components.url.stripHash Function 4-8 (urlStore const has no node)
await mcp.codebase_memory.get_code_snippet({ project: "refined-github", qualified_name: "refined-github.source.components.url.stripHash" });
// served source byte-identical to checkout read @ pin 3187161
```
Executed 2026-08-29 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the refresh-on-subscribe pattern for any module-scoped readable store over a mutable source, and the one-listener-per-subscriber binding to the host navigation event — both are host-agnostic Svelte mechanics. Adapt the event source (Turbo `navigation` global here), the strip policy (hash-only), and the consumer grammars. Omit the RGH-specific id extraction regexes beyond the route-predicate-first branching shape. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on components/url.ts + rgh-feature-descriptions.svelte; no direct test upstream (browser-bound) — deterministic pins stand in; `urlStore` graph-node absent (source-read citation). Cross-reference: extensible-nav-store-tab-store.md (sibling store plane), react-page-update-signal.md (the non-Svelte side of the same soft-nav problem), url-hash-replacestate-cleanup.md (hash as ephemeral state — complementary to hash-stripping here).
