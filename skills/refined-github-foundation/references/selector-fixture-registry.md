<!-- capsule-v2 -->
# selector-fixture-registry — how do you keep CSS selectors for a mutating host honest, versioned, and testable without a browser farm?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What convention binds every production CSS selector to live-URL evidence, and what is the current health status of that mechanism?

## `<selector>` / `<selector>_` paired-export registry
**Path/Symbol:** `source/github-helpers/selectors.ts` (whole file; e.g. `branchSelector` :19–24 + `branchSelector_` :25–34); validator `source/github-helpers/selectors.test.ts` (:35–70).
**Signature:** Every selector export is a `string` (or `[sel1, sel2, …]` alternatives array); its sibling `<name>_` is a `UrlMatch[]` = `[expectations: number, url: string][]` (`satisfies UrlMatch[]`).
**Data Shape:** `expectations` = EXACT match count required on that URL. Alternatives arrays encode layout variants with per-variant comments ("sidebar closed" vs "open"; JS-added elements; deprecated selectors carry `// TODO [2027-01-01]: Drop` expiry comments).

### Decisive source
```ts
export const branchSelector = [
	'#ref-picker-repos-header-ref-selector-wide', // `isSingleFile` with sidebar closed
	'#ref-picker-repos-header-ref-selector',      // `isSingleFile` with sidebar open; `isRepoRoot`
	// TODO [2027-01-01]: Drop
	'[data-hotkey="w"]',
];
export const branchSelector_ = [
	[1, 'https://github.com/refined-github/refined-github'],
	[0, 'https://github.com/refined-github/refined-github/blob/main/readme.md'], // Added via JS :(
	[1, 'https://github.com/refined-github/sandbox/tree/branch/with/slashes'],
] satisfies UrlMatch[];
```

**Flow (validator):** enumerate module exports → skip `*_` URL arrays → for each selector fetch its pinned URLs (pMemoize + FILESYSTEM cache under `./test/.cache/` via filenamify keys) → write each into a blank document → assert `$$(selector).length === expectations` per row.
**Invariant:** A selector WITHOUT a `_<name>` array fails the suite ("No URLs defined") — evidence is structurally mandatory, not aspirational; expectations counts catch BOTH regressions (count drops) and silent successes on pages where the element never existed.
**Probe/status:** `selectors.test.ts:49` — the suite is currently `describe.concurrent.skip` with two recorded reasons: upstream breakage (issue #9314) and happy-dom failing to parse these selectors (needs jsdom or real browser). The REGISTRY convention remains fully in force and machine-checkable; only the automated validator is parked. Caveat recorded here rather than claiming a green run.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "branchSelector directoryListingFileIcon", limit: 10 });
// → refined-github.source.github-helpers.selectors.* Constants source/github-helpers/selectors.ts
```

## Verdict
Adopt the paired-export registry (`selector` + `selector_` evidence rows with exact-count expectations) for ANY extension fighting a moving host UI — it converts selector rot from bug reports into data. Adapt the fixture cache location and the URL corpus to your target site. Omit the skipped-runner state (transient infra), but record it honestly as done here.
