<!-- capsule-v2 -->
# readme-feature-metadata-parser — how do you keep a 190-feature catalog's documentation honest, mechanically?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How can a large plugin/feature repo make its README a machine-checked build contract — every feature documented, screenshot-attached, and consistent with the import manifest — without a docs framework?

## Regex extraction from README + entry manifest, snapshot-pinned
**Path/Symbol:** `build/readme-parser.ts` — `simpleFeatureRegex` :6, `highlightedFeatureRegex` :7–8, `extractDataFromMatch` :15–51, `getFeaturesMeta` :53–58, `getImportedFeatures` :60–65 (whole file 65 lines); `build/readme-parser.test.ts` (whole file 23 lines); `build/features.test.ts` — `validateReadme` :99–115, `validateCss` :117–141, `validateTsx` :157–197, per-file runner :243–266.
**Signature:** `getFeaturesMeta(): FeatureMeta[]` (`{id, description: string(HTML), css?: true, cssOnly?: true, screenshot: string|null}`); `getImportedFeatures(): FeatureId[]`.

### Decisive source
```ts
// Group names must be unique because they will be merged
const simpleFeatureRegex = /^- \[\]\(# "(?<simpleId>[^"]+)"\)(?: 🔥)? (?<simpleDescription>.+)$/gm;
const featureRegex = regexJoinWithSeparator('|', [simpleFeatureRegex, highlightedFeatureRegex]);
// extractDataFromMatch (simple branch):
const hasCss = existsSync(`source/features/${simpleId}.css`);
const hasTsx = existsSync(`source/features/${simpleId}.tsx`);
return {
	id: simpleId as FeatureId,
	description: parseMarkdown(linkLessMarkdownDescription),
	css: hasCss || undefined,          // `undefined` hides the key when CSS is missing
	cssOnly: (hasCss && !hasTsx) || undefined,
	screenshot: urls.find(url => screenshotRegex.test(url)) ?? null, // `null` keeps the key visible
};
// getImportedFeatures — the manifest is parsed BY REGEX, not imported:
return [...contents.matchAll(/^import '\.\/features\/(?<id>[^.]+)\.js';/gm)]
	.map(match => match.groups!.id as FeatureId).toSorted((a, b) => a.localeCompare(b));
```

**Flow:** CI reads readme.md → two named-group regexes (joined with `regexJoinWithSeparator('|')`) match simple list entries and highlighted `<p><a title=…><img>` entries → markdown descriptions are link-stripped then `parseMarkdown`'d to HTML → file existence probes add `css`/`cssOnly` flags → output is sorted by id and pinned to `__snapshots__/features-meta.json`; the entry manifest `source/refined-github.ts` is regex-scanned for `import './features/<id>.js';` lines (the `[^.]+` id class EXCLUDES `.css` imports) and pinned to `__snapshots__/imported-features.json`. Separately, `features.test.ts` walks `source/features/*` file-by-file and asserts the cross-invariants.
**Invariant:** (1) README is the SOURCE OF TRUTH for feature metadata — parser drift fails CI via file snapshots; (2) the entry manifest is analyzed as TEXT (regex), keeping the parser dependency-free and runnable before any bundling; (3) undefined-vs-null JSON semantics are deliberate: `undefined` HIDES keys (`css`, `cssOnly`), `null` KEEPS them visible (`screenshot`) — downstream consumers rely on key presence; (4) every public feature must be documented with ≥20-char description, a screenshot (png/gif or rgh-assets/user-attachments URL) unless in the explicit `noScreenshotExceptions` set (each entry justified inline), and appear exactly once; private features (`isFeaturePrivate`) are exempt; (5) `import.meta.glob(['../readme.md', '../source/refined-github.ts'])` in the test registers those readFileSync'd files as vitest dependencies so edits re-run the suite (vitest discussion #5864 pattern); (6) banned combinations are enforced per-file: `deduplicate` × `observe()` (observer already dedupes) and `deduplicate` × `delegate(signal)` (listener may be removed and not restored — issue #5871); v4-API features must declare `requiresToken: true` or use `hasToken`.
**Probe:** DIRECT TESTS read in full: `build/readme-parser.test.ts` (snapshot pin of both outputs + glob re-run registration) and `build/features.test.ts` (per-file invariant engine, 266 lines). Executed pins: `grep -n "regexJoinWithSeparator|existsSync|cssOnly|readFileSync('readme.md'" build/readme-parser.ts` → 2, 9, 13, 39, 40, 47, 54, 62. Runner block: no node_modules at checkout → `vitest --run` cannot execute here; test CONTENT is cited from direct reads, not from a run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", qn_pattern: "build.readme-parser.*", limit: 30 });
// total: 16 → 2 entry fns + 6 regex vars + extractDataFromMatch/urlExtracter + both test modules
```
Executed 2026-08-27 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the README-as-build-contract pattern for any large plugin/feature catalog: regex-extract metadata from the doc, snapshot-pin the extraction, and run a per-file invariant engine that cross-checks doc ↔ manifest ↔ source (token gates, banned helper combinations, screenshot policy with an explicit exception set). Adopt the `import.meta.glob` dependency-registration trick for any test that reads files outside the import graph. Adapt the two doc regexes to your README format (keep group names unique across joined alternatives); omit the GitHub-specific screenshot URL classes and the 🔥 highlight marker. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; direct tests exist and were read in full but NOT executed (no node_modules at checkout — standing runner block).
