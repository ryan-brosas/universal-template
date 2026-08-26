<!-- capsule-v2 -->
# Content clipping toolkit — how do clip, clipSentence, and firstLine avoid mid-word/mid-surrogate cuts?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which shared string primitives bound every downstream extractor, and what are their fallback orders?

## content.ts primitives (`src/compaction/content.ts`) + skill collapse (`src/compaction/skill-collapse.ts`)
**Path/Symbol:** `content.ts:clip` (:3-14), `clipSentence` (:21-32), `nonEmptyLines` (:34-38), `firstLine` (:40), `textOf` (:42-48); `skill-collapse.ts:collapseSkillLines/collapseSkillText` (:7-35).
**Signature:** `clip(text, max=200)`; `clipSentence(text, max=200)`; `firstLine(text, max=200)`.
**Data Shape:** clip: word-boundary cut accepted only if ≥60% of max (`cut > max*0.6`), surrogate-pair guard backs off one char; clipSentence: last `.!?`+space within [50%·max, max], else falls back to clip.

### Decisive source
```ts
const cut = text.lastIndexOf(' ', max);
let end = cut > max * 0.6 ? cut : max;              // hard cut if word boundary too early
if (end > 0 && end < text.length) {
  const code = text.charCodeAt(end - 1);
  if (code >= 0xd800 && code <= 0xdbff) end--;       // don't split a surrogate pair
}
return text.slice(0, end);                           // NO ellipsis — callers add markers

// skill blocks → "[skill: name]" placeholders (dedup by name in line mode)
const SKILL_TAG_RE = /^-?\s*<skill\s+name="([^"]+)"/;
```

**Flow:** these primitives are the ONLY way any extractor shortens text (goals, preferences, outstanding items, turn summaries, error bodies) — no ad-hoc slicing downstream. `textOf` joins multi-part text content with '\n' so block extraction sees one string. Skill collapse runs BEFORE goal/preference filtering and user truncation so injected skill payloads never consume budget.
**Invariant:** (1) Primitives return UNDECORATED strings — ellipses/`(truncated)` markers are added by callers, keeping policy out of the toolkit. (2) The 0.6 threshold means a long final word is hard-cut rather than emitting a uselessly short prefix. (3) Sentence clipping requires the punctuation INSIDE the window AND at ≥half the budget — earlier sentence-ends lose to word-boundary fallback.
**Probe:** constants/thresholds pinned at content.ts :7/:29; used-by census `grep -c "clipSentence\|firstLine(\|clip(" src/compaction/*.ts src/compaction/extract/*.ts` ≥ 20 sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "clip clipSentence firstLine nonEmptyLines", limit: 8 });
```

## Verdict
Adopt the four primitives as a shared toolkit before porting any extractor capsule from this foundation. Adapt thresholds freely — keep the no-decoration contract. Omit skill collapse without skill injections.
