<!-- capsule-v2 -->
# pattern-taxonomy-false-positive-boundary — which patterns flag AI prose, and what never counts as proof alone?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** How do I port a "signs of AI writing" detector that stays useful — i.e., flags real tells without accusing every polished or dry human writer?

## 35 numbered patterns in five category groups, plus an explicit not-flag list
**Path/Symbol:** `SKILL.md` — pattern groups `## Content patterns` §1–6 (:48–108), `## Language and grammar patterns` §7–13 (:110–177), `## Style patterns` §14–19 (:179–232), `## Chatbot patterns` §20–22 (:234–263), `## Filler and hedging` §23–35 (:265–391); boundary `## Check for false positives` → `### What not to flag` (:393–416) and `### Human details to keep` (:418–428).
**Data Shape:** Each of the 35 patterns is a fixed-shape block: *Words to watch* (literal trigger phrases), *Problem* (why it is an AI tell), **Before** (flagged example), **After** (humanized rewrite). Pattern numbers are stable cross-references (`§14`, `§7`) used by other sections.

### Decisive source
```markdown
When unsure, look for several patterns together. One em dash proves nothing.
Several stock patterns in the same passage are stronger evidence.
```
(SKILL.md :416 — the stacking rule that makes the taxonomy a classifier prior instead of a naive keyword ban.)

**Flow:** Detection scans for literal watched phrases per category (inflated legacy claims, sales language, vague sources → stock AI words, is/are avoidance, forced triads, dash abuse → bold/emoji/title-case/curly-quote decoration → chatbot leftovers, agreeable tone → filler, qualifiers, fake-deeper-truth, fake-candid openers, unanswered objections, rejected fake alternatives). Before any rewrite, the boundary pass vetoes single-tell accusations: 16 explicit not-flag items include perfect grammar, mixed registers, generic dryness, formal words, letter salutations, one transition word, curly quotes alone, em dashes alone, one dramatic fragment, deliberate repeated openings, mid-sentence "honestly", useful limits/disclaimers, REAL alternatives in design docs, unsourced claims generally, clean formatting from templates, and secondhand text inside quotations/titles/proper names/examples. A keep-list protects human voice: specific odd details, mixed feelings, era-bound slang, deliberate first-person choices, sentence-length variety, genuine self-corrections, and anything edited before November 30, 2022 (ChatGPT's public launch).

**Invariant:** No single surface tell may drive a verdict; evidence = several stacked tells in the same passage. Watched-phrase matching must skip text where the phrase is discussed rather than used. The writer's-sample override outranks the pattern list (voice habits, including dash rate, are kept).

**Probe:** Deterministic content probes executed: direct reads pin the stacking rule at :416, the em-dash-alone veto at :406–407 ("Em dashes alone. Many editors and journalists use them often…"), the secondhand-text exemption at :414, and the pre-2022 heuristic at :428. Repo-owned validator `python3 scripts/validate-package.py` exit 0 pins that all `### N.` headings are present and ordered, so the section numbers cited here resolve. No executable prose test exists — recorded caveat.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", label: "Section", limit: 50 })
```
(returns the first 50 of 74 Section nodes with has_more=true — page with offset to reach the rest; includes every `humanizer.SKILL.<N>.<pattern-name>` node with its heading line anchor. BM25 over Section text returns zero rows on this graph — enumerate by label.)

## Verdict
Adopt the two-list structure — trigger patterns PLUS an explicit not-flag boundary with a stacking rule — as the portable core; without the boundary the detector false-positives on professionals. Adopt the fixed per-pattern block shape (watch-words/problem/before/after) as a corpus authoring format. Adapt the specific phrase lists to your domain and language; they are Wikipedia-derived English tells. Omit the pre-2022 dating heuristic only if your corpus postdates LLM ubiquity entirely.
