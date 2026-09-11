<!-- capsule-v2 -->
# Goal + preference extraction — how do session goals survive scope changes and stay uncontaminated by pasted noise?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which regex gates separate real goals/preferences from chatter, pasted output, and command templates — and how are scope changes represented?

## extractGoals (`src/compaction/extract/goals.ts`) + extractPreferences (`src/compaction/extract/preferences.ts`)
**Path/Symbol:** `goals.ts:extractGoals` (:47-79), `SCOPE_CHANGE_RE` (:5-6), `TASK_RE` (:8-9), `NON_GOAL_RE` (:16-17), `TEMPLATE_SIGNAL_RE` (:21-22), `LEADING_CHARS=200` (:45); `preferences.ts:extractPreferences` (:14-42), `PREF_PATTERNS` (:5-12).
**Signature:** `(blocks) => string[]`; goals capped 8 lines (first block up to 6), preferences capped 10 with ONE per user block.
**Data Shape:** Goals emit a literal `[Scope change]` marker followed by the replacing bullets; preference dedup is case-insensitive on clipped text.

### Decisive source
```ts
// Scope-change / task intent tested ONLY on the LEADING 200 chars of a user block
// so pasted outputs below the actual instruction do not trigger matches.
const leading = b.text.slice(0, LEADING_CHARS);
if (SCOPE_CHANGE_RE.test(leading))        latestScopeChange = lines.slice(0, 3)...;
else if (TASK_RE.test(leading) && lines[0].length > 15) latestScopeChange = lines.slice(0, 2)...;
// Command-template truncation: stop collecting at template-signal lines
const idx = lines.findIndex(l => TEMPLATE_SIGNAL_RE.test(l));   // "For each", "Do NOT implement", ...
// NON_GOAL rejects pasted tables/paths/code/URLs: ^[│├└─╭╰], ```, =MACRO(, https?:, \n literals
```
Preference gates: line must be 5–200 chars, NOT a question (`?` reject), match a TIGHTENED pattern requiring verb+object (`prefer(s|red|ring)?\s+\w`, `don'?t want`, `always/never <verb>`, `please <verb>`, `style|format|language|naming[:=]`).

**Flow:** first substantive user block seeds up to 6 goal lines; later blocks can only REPLACE the trailing scope-change slot (never append mid-list); the `[Scope change]` marker is emitted only if replacement bullets were actually captured. Preferences run per-block with a `++perBlock >= 1` break — one rule per message prevents pasted rule-lists flooding the section. Finally `dedupPreferencesAgainstGoals` removes preference strings identical to goal lines.
**Invariant:** (1) Leading-200-char testing is THE paste-defense: scope detection never reads below the instruction. (2) Goals list is append-only except for the reserved scope-change tail — history is preserved, intent is current. (3) Preference patterns require a VERB after the keyword ("always use" matches, bare "always" doesn't). (4) Questions are never preferences.
**Probe:** `tests/full-fidelity-snapshot.test.ts` `extracts goals from user messages` (:160-171); regex pins at goals.ts :5-22 and preferences.ts :5-12.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractGoals SCOPE_CHANGE_RE TEMPLATE_SIGNAL dedupPreferencesAgainstGoals", limit: 8 });
```

## Verdict
Adopt leading-window scope detection, template-truncation, and verb-anchored preference patterns as a set. Adapt regex vocabularies to your users' phrasing. Omit the [Scope change] marker convention only if you replace it with equivalent explicit-intent signaling.
