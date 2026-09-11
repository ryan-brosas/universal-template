<!-- capsule-v2 -->
# Candidate parse pipeline — how does one candidate string become zero or more structured Candidates without throwing?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** When porting a utility-class parser, where must parsing fail silently vs. yield multiple results, and in what order are variants parsed and stored?

## parseCandidate generator (string → Candidate*)
**Path/Symbol:** `packages/tailwindcss/src/candidate.ts:317` — `parseCandidate` (:317–613).
**Signature:** `function* parseCandidate(input: string, designSystem: DesignSystem): Iterable<Candidate>`.
**Data Shape:** Input raw class string; reads `designSystem.theme.prefix`, memoized `designSystem.parseVariant` / `designSystem.utilities.has(root, kind)`. Output: iterable of `{kind: 'static'|'functional'|'arbitrary', variants: Variant[], important, raw}`; empty iterable = invalid candidate (no errors thrown).

### Decisive source
```ts
let rawVariants = segment(input, ':')
if (designSystem.theme.prefix) {
  if (rawVariants.length === 1) return null          // prefix required
  if (rawVariants[0] !== designSystem.theme.prefix) return null
  rawVariants.shift()                                 // consumed here, invisible later
}
let base = rawVariants.pop()!
for (let i = rawVariants.length - 1; i >= 0; --i) {   // RIGHT to LEFT
  let parsedVariant = designSystem.parseVariant(rawVariants[i])
  if (parsedVariant === null) return
  parsedCandidateVariants.push(parsedVariant)
}
// ... trailing `!` wins over legacy leading `!`
if (base[base.length - 1] === '!') { important = true; base = base.slice(0, -1) }
else if (base[0] === '!')          { important = true; base = base.slice(1) }
// static match yields IN ADDITION to functional roots below (not either/or)
if (designSystem.utilities.has(base, 'static') && !base.includes('[')) { yield { kind: 'static', ... } }
```

**Flow:** segment on top-level `:` → prefix gate/strip → pop base → parse variants right-to-left into application order (`focus:hover:flex` stores `[hover, focus]`) → strip important marker (suffix preferred, legacy prefix accepted) → static short-circuit yield → `/` modifier split (≥2 slashes invalid) → arbitrary-property branch (`[p:v]`) OR root discovery (`[…]`, `(--)`, findRoots) → yield one functional candidate per discovered root.
**Invariant:** Every rejection path is an early `return` from the generator — the parser never throws for malformed input; validity is communicated purely by "did anything get yielded". The prefix segment is removed before variant parsing so no downstream code knows prefixes exist.
**Probe:** `packages/tailwindcss/src/candidate.test.ts:118` (`focus:hover:flex` snapshot pins stored variant ORDER), `:1817` (prefix required-first gate), `:53`/`:70` (important + negative roots).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "parse candidate variant utility combinator", limit: 10, fields: ["signature", "lines"] });
```
Executed live this pass: returned `candidate.parseCandidate` :317–613, `candidate.parseVariant` :662–850, `candidate.parseModifier` :615–660; `trace_path(direction:"both")` on parseCandidate shows callees {findRoots, parseModifier, parseVariant, decodeArbitraryValue, segment, isValidArbitrary} and runtime entry via memoized `design-system.parseCandidate`.

## Verdict
Adopt the fail-silent generator contract, right-to-left variant parsing with application-order storage, dual important syntax with suffix precedence, and multi-yield semantics. Adapt the DesignSystem plumbing (memoization wrappers live in design-system.ts). Omit the exact Tailwind root grammar if your DSL has different delimiters — but keep "one rejection channel = empty result" so upstream invalid-candidate feedback stays uniform.
