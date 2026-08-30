<!-- capsule-v2 -->
# cross-file-numbering-and-rules-parity — how do skill and README stay number-complete and rule-present without sharing order?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** When two documents mirror the same numbered catalog with different groupings, what comparison semantics keep them consistent without forcing identical layout?

## Ordered-list numbering in the skill vs complete-set numbering in README, plus exact-string rule presence
**Path/Symbol:** `scripts/validate-package.py` :72–77 (`pattern_numbers`, ordered) and :79–83 (`readme_numbers`, set); :55–70 (`plain_language_rules` presence in AGENTS.md).
**Signature:** no function — three module-level checks.
**Data Shape:** SKILL side: every `### N. ` heading number as an ORDERED list, compared `!= list(range(1, 36))`. README side: every table-row leading number `| N |` as a SET, compared `!= set(range(1, 36))`. AGENTS side: six literal strings, each a substring test.

### Decisive source
```python
pattern_numbers = [
    int(number)
    for number in re.findall(r"(?m)^### ([0-9]+)\. ", SKILL)
]
if pattern_numbers != list(range(1, 36)):
    raise SystemExit(f"Number SKILL.md patterns from 1 through 35: {pattern_numbers}")

readme_numbers = {
    int(number) for number in re.findall(r"(?m)^\| ([0-9]+) \|", README)
}
if readme_numbers != set(range(1, 36)):
    raise SystemExit("List patterns 1 through 35 in the README table")
```
(:72–83. List equality enforces order AND contiguity; set equality enforces completeness only.)

**Flow:** extract heading numbers from SKILL.md → demand exactly 1..35 IN SEQUENCE (prose cross-references like "§14" and "§7" are stable only if ordering is frozen; AGENTS.md :23 makes renumbering a coordinated event: "update the README table, heading, validator, and every pattern reference") → extract row numbers from README tables → demand {1..35} as a set, because README groups rows by CATEGORY tables whose union is intentionally out of numeric order (Style table lists 14–19 then 26–35; Chatbot 20–22; Filler 23–25) → separately (:55–70), require six exact plain-language strings to appear anywhere in AGENTS.md ("## Writing style", "Lead with the main point.", "Use common words and active voice.", "Keep sentences and paragraphs short.", "Use `must` for requirements.", "Keep the full technical meaning."), reporting any missing ones by name.

**Invariant:** The skill's numbering is a load-bearing API (stable §-references across sections and versions); the README's obligation is coverage, not order; the style rules are enforced as literal presence so an editor cannot silently drop the house writing standard. All three checks fail with messages that enumerate exactly what is missing or misnumbered.

**Probe:** Deterministic probes executed: direct read of SKILL.md confirms headings run `### 1.` through `### 35.` sequentially (spot-pinned at :50/:112/:181/:236/:267/:382); direct read of README :57–115 confirms all-row completeness with the out-of-order category block at :90–99; direct read of AGENTS.md :29–43 confirms all six rule strings present verbatim; validator GREEN run exercised all three gates live (exit 0). Mutation RED blocked by read-only checkout — recorded caveat.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", qn_pattern: "pattern_numbers|readme_numbers|plain_language_rules" })
```

## Verdict
Adopt the asymmetric comparison discipline — ORDER where documents cross-reference each other, SET where they merely catalog, EXACT-STRING presence for standards you cannot afford to lose. Adopt fail-messages that print the offending sequence/missing names. Adapt the extraction regexes to your heading/row grammar and your own rule strings; keep them literal, not paraphrased.
