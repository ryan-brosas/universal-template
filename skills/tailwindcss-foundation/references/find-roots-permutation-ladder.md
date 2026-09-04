<!-- capsule-v2 -->
# findRoots permutation ladder — how is the root/value split of `bg-red-500` discovered without a registry of full class names?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** How does a parser resolve which leading segment of a dash-joined class name is the registered utility root, and which dash boundaries are special-cased?

## findRoots generator (dash-permutation root discovery)
**Path/Symbol:** `packages/tailwindcss/src/candidate.ts:852` — `findRoots` (:852–906), consumed by `parseCandidate` (:524) and `parseVariant` (:722).
**Signature:** `function* findRoots(input: string, exists: (input: string) => boolean): Iterable<Root>` where `Root = [root: string, value: string | null]`.
**Data Shape:** `exists` is an injected registry predicate (`utilities.has(root,'functional')` or `variants.has(root)`); yields every matching split, longest value first.

### Decisive source
```ts
// If there is an exact match, then that's the root.
if (exists(input)) yield [input, null]
let idx = input.lastIndexOf('-')
while (idx > 0) {
  let maybeRoot = input.slice(0, idx)
  if (exists(maybeRoot)) {
    let root: Root = [maybeRoot, input.slice(idx + 1)]
    if (root[1] === '') break            // `bg-` → invalid named value, stop
    // `@-…`: `@` followed by `-` must not be confused with the @ root
    if (root[0] === '@' && exists('@') && input[idx] === '-') break
    yield root
  }
  idx = input.lastIndexOf('-', idx - 1)
}
// Try '@' variant AFTER permutations so `@max-foo-bar` matches `@max` first
if (input[0] === '@' && exists('@')) yield ['@', input.slice(1)]
```

**Flow:** exact whole-string match (valueless root) → strip successively shorter dash-delimited suffixes from the right → each existing prefix yields `[prefix, remainder]` → trailing-`@` fallback last. Callers iterate all yielded roots and emit one candidate per root, so `bg-red-500` can legally compile under both a hypothetical `bg-red` and `bg` root.
**Invariant:** Permutations go strictly right-to-left by dash index; an empty remainder (`foo-`) terminates instead of yielding an invalid named value. The `'@'` bare root is only tried after all dash permutations, giving longer `@x` roots priority over the catch-all `@`.
**Probe:** `packages/tailwindcss/src/candidate.test.ts:491` (`flex-`/`bg-` parse to `[]`), `:1419` (`@lg:flex` against functional `@` root → `{root:'@', value:{kind:'named', value:'lg'}}`), `:1449` (`@foo-bar` keeps whole remainder as one named value).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "functional variant starting with @ hyphen", limit: 10, fields: ["signature", "lines"] });
```
Executed live this pass via BM25 seam searches ("parse candidate variant utility combinator") plus direct read of :852–906; `segment` fan-in 53 and cluster 89 (`segment;convert;decodeArbitraryValue;isLength;parseCandidate`) locate this as the shared root-discovery kernel for both utilities and variants.

## Verdict
Adopt permutation-based root discovery over any static list of valid class names — it is what makes arbitrary theme scales work without registering every value. Adapt the `@` special case to your own reserved prefix character. Omit nothing structural: dropping the empty-value break or the post-permutation `@` fallback silently changes which candidates are accepted.
