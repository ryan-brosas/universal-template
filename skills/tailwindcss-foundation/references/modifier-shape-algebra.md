<!-- capsule-v2 -->
# Modifier shape algebra — when does `/50` parse, and what exactly does an unparsable modifier invalidate?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** Which modifier syntaxes must a utility engine accept, and is a bad modifier "no modifier" or "no candidate"?

## parseModifier (three-shape discriminated result)
**Path/Symbol:** `packages/tailwindcss/src/candidate.ts:615` — `parseModifier` (:615–660); enforced at `parseCandidate` :384–399.
**Signature:** `function parseModifier(modifier: string): CandidateModifier | null` with `CandidateModifier = {kind:'arbitrary', value} | {kind:'named', value}`.
**Data Shape:** Input is the text after the first top-level `/`. Output null means unparsable — which propagates as *whole-candidate invalid*, not "modifier dropped".

### Decisive source
```ts
function parseModifier(modifier: string): CandidateModifier | null {
  if (modifier[0] === '[' && modifier[modifier.length - 1] === ']') {
    let arbitraryValue = decodeArbitraryValue(modifier.slice(1, -1))
    if (!isValidArbitrary(arbitraryValue)) return null
    // Empty arbitrary values are invalid. E.g.: `data-[]:`
    if (arbitraryValue.length === 0 || arbitraryValue.trim().length === 0) return null
    return { kind: 'arbitrary', value: arbitraryValue }
  }
  if (modifier[0] === '(' && modifier[modifier.length - 1] === ')') {
    // Drop the `(` and `)` characters
    modifier = modifier.slice(1, -1)

    // A modifier with `(…)` should always start with `--` since it
    // represents a CSS variable.
    if (modifier[0] !== '-' || modifier[1] !== '-') return null

    // Values can't contain `;` or `}` characters at the top-level.
    if (!isValidArbitrary(modifier)) return null

    // Wrap the value in `var(…)` to ensure that it is a valid CSS variable.
    modifier = `var(${modifier})`

    let arbitraryValue = decodeArbitraryValue(modifier)

    return { kind: 'arbitrary', value: arbitraryValue }
  }
  if (!IS_VALID_NAMED_VALUE.test(modifier)) return null   // /^[a-zA-Z0-9_.%-]+$/
  return { kind: 'named', value: modifier }
}
```
**Note:** unlike arbitrary *values*, the `(…)` modifier shorthand wraps into `var(…)` itself (candidate.ts:644) before decoding.

And the enforcement that makes modifiers load-bearing:
```ts
let [baseWithoutModifier, modifierSegment = null, additionalModifier] = segment(base, '/')
if (additionalModifier) return                                   // bg-red-500/50/50 → invalid
let parsedModifier = modifierSegment === null ? null : parseModifier(modifierSegment)
// Empty arbitrary values are invalid...
if (modifierSegment !== null && parsedModifier === null) return  // bad modifier kills candidate
```

**Flow:** `[x]` → decode + validate + reject empty → arbitrary · `(x)` → require `--x`, wrap `var(--x)`, decode → arbitrary · else named iff it matches `[a-zA-Z0-9_.%-]+`. More than one top-level `/` rejects outright.
**Invariant:** A present-but-invalid modifier invalidates the entire candidate (`bg-[#0088cc]/[]` yields nothing); there is no silent fallback to the unmodified candidate. Static utilities never reach modifier parsing at all — their yield happens before the `/` split, so `flex/foo` is invalid by construction.
**Probe:** `packages/tailwindcss/src/candidate.test.ts:405` (arbitrary modifier), `:913`/`:1087` (implicit `(--)` variable modifiers), `:1183` (invalid arbitrary shorthand modifier rejected), `:500–519` (static-with-modifier and double-modifier all `[]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "parse candidate variant utility combinator", limit: 10, fields: ["signature", "lines"] });
```
Executed live this pass; `candidate.parseModifier` returned at :615–660 between parseCandidate (:317–613) and parseVariant (:662–850), confirming single shared modifier parser for both candidates and variants.

## Verdict
Adopt the three-shape algebra and especially the strictness rule (bad modifier ⇒ no candidate) plus the implicit-var shorthand `(…)`→`var(…)`. Adapt the named-value charset to your grammar. Omit Tailwind's specific `isValidArbitrary` character policy only if you have an equivalent top-level-safety check (`;`/`}` rejection).
