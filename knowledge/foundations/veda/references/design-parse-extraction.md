<!-- capsule-v2 -->
# Design-block extraction — how do you pull a structured program design out of a free-form LLM response with a dependency-free regex parser that fails soft per section?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you parse a constrained XML subset embedded in an LLM's prose (with possible draft attempts before the final block) without an XML dependency, and what exactly may fail vs. degrade?

## Connected graph-selected seam
**Path/Symbol:** `src/core/design/parse.ts:parseProgramDesign` (:153–183) over helpers `PROGRAM_RE` (:26), `decodeEntities` (:29–36), `attr` (:39–43), `children` (:46–60), `selfClosing` (:63–71), `clean` (:74–76), and the per-section parsers `parseLayout/parseContext/parseTypes/parseSignatures/parseCallstacks/parseInvariants` (:78–146).
**Signature:** `parseProgramDesign(response: string): ParseResult` where `ParseResult = { ok:false, reason:'no-program-block' } | { ok:false, reason:'malformed', detail } | { ok:true, xml, design }`.
**Data Shape:** `ProgramDesign = { name, task, intent, layout: DesignFile[], context: DesignContextEntry[], types[], signatures[], callstacks[], invariants[] }`; `<used>` vs `<omitted>` is encoded by `reason` presence (`reason === undefined` ⇒ used).

### Decisive source
```ts
/** Match the outermost <program ...>...</program> block (last one wins). */
const PROGRAM_RE = /<program\b([^>]*)>([\s\S]*?)<\/program>/gi;
export function parseProgramDesign(response: string): ParseResult {
  const matches = [...response.matchAll(PROGRAM_RE)];
  if (matches.length === 0) return { ok: false, reason: 'no-program-block' };
  const last = matches[matches.length - 1];          // drafts before final are ignored
  // ...
  const intentMatch = body.match(/<intent\b[^>]*>([\s\S]*?)<\/intent>/i);
  if (!intentMatch) return { ok: false, reason: 'malformed', detail: 'missing <intent> element' };
  /* every other section parses independently and filters its own items:
     .filter(f => f.path) / .filter(s => s.name && s.file) / etc. */
```

**Flow:** find all `<program>` blocks case-insensitively → take the LAST → hard-fail only if none exists or `<intent>` missing → otherwise run six independent section parsers whose items individually drop out when their required attributes (`path`, `name`+`file`, `ref`) are absent → return both raw `xml` and parsed `design`.
**Invariant:** purity ("string in, ParseResult out, no I/O" — module docblock); exactly two failure modes (`no-program-block`, `malformed`+detail); everything else degrades to empty arrays; attribute values accept `"…"` or `'…'`, are entity-decoded (`&amp;&lt;&gt;&quot;&#39;`); `clean()` canonicalizes bodies (CRLF→LF, per-line trim, blank-line collapse, entity decode); paired and self-closing element forms are collected by *separate* regexes so `<file path="x"/>` inside `<layout>` parses.
**Probe:** `bun src/core/design/__probe__.ts` (repo-owned backtest, runner named in its header) executed at pin: **19/19 assertions ALL GREEN**, including wrapped-in-prose extraction, `omitted reason` decoding, `returns description 'count evicted'`, and `validation ok:true`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "parseProgramDesign attr children selfClosing decodeEntities program block", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the last-block-wins + single-hard-failure + per-item-soft-drop grammar for any structured artifact you ask a model to embed in prose. Adapt the tag vocabulary and required-attribute sets to your format. Omit nothing behavioral; keep the parser pure and pair it with a separate validation layer (see design-validate-write-gate) rather than folding checks into parsing.
