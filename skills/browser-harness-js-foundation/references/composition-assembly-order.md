<!-- capsule-v2 -->
# Composition assembly order — in what grammar does a brief become a composition, and what does the header carry?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How are cards, action beats, and explanation cards ordered, and what does the compiled composition embed beyond `beats`?

## intro → actions with spliced afterAction explanations → outcome; header embeds the whole style

**Path/Symbol:** `skills/cdp/sdk/video.ts:compileBrief` (:409-509) — `explanationByAction` map (:438-458), beat assembly (:461-479), composition header (:488-506), final privacy gate (:507).
**Signature:** `compileBrief(summary, brief, style = HOUSE_STYLE, revealedText = new Map()): Json` → `{ schemaVersion, viewport, cursorStart, frameStyle, readingWpm, pacing, durationBudget, bg, plan, motion, privacy, redact, beats }`.
**Data Shape:** `explanations[].afterAction` is a 1-BASED index into `brief.actions`; the composition is persisted by `writeComposition` (:511-513) as `window.COMPOSITION = {…};` — a JS file, not JSON.

### Decisive source
```ts
explanationByAction.set(item.afterAction, [...(explanationByAction.get(item.afterAction) || []), card]);
...
const beats: Json[] = [{ card: true, kind: 'intro', title: task, ... }];   // intro card FIRST
brief.actions.forEach((raw, index) => {
  const [beat, target] = compileAction(raw, index, events, plan, firstTs, previousTarget, viewport, pacing, revealedText);
  previousTarget = target;
  beats.push(beat, ...(explanationByAction.get(index + 1) || []));          // splice AFTER each action
});
const outcomeTitle = requireText(brief.outcomeTitle || 'Task complete', 'outcomeTitle');
beats.push({ card: true, kind: 'outcome', ... });                           // outcome card LAST
...
validatePrivacy(reviewed, redact, composition);   // against the ASSEMBLED composition
```

**Flow:** viewport is PINNED from the first action's event before any beat exists (:420-422) → every explanation compiles to a card and buckets under its 1-based `afterAction` → assembly walks actions in brief order, pushing each compiled beat followed by that bucket's cards (multiple explanations on one action keep their list order) → the outcome card closes the timeline (title defaults to 'Task complete' when omitted) → cadence gates, holds, and budget run over the FULL beat list → the header copies style fields verbatim (viewport, cursorStart, frameStyle, readingWpm, pacing, motion, background, privacy pad/mask) plus `durationBudget`, plan, and redactions → `validatePrivacy` checks reviewed/redact coverage against `usedFrames` OF THE ASSEMBLED beats.
**Invariant:** (1) The timeline is fixed grammar — intro/actions/outcome with explanations only BETWEEN beats; nothing can render before the intro or after the outcome because those cards are compiler-inserted, not author-supplied. (2) The composition is SELF-DESCRIBING: it embeds the exact style numbers it was compiled with, so the renderer never reads HOUSE_STYLE separately and export can detect compile/render drift. (3) Privacy validation runs on the assembled artifact, so a frame used only by a spliced explanation or the outcome still must be reviewed.
**Probe:** direct tests pin the grammar end-to-end ('recording initialization hides typing…' :53-62 asserts beats[1] is the first ACTION beat after the intro card; explicit-reveal test :75-76 asserts `shown.beats[2].type.text`). Deterministic pins: `grep -n "explanationByAction\|kind: 'intro'\|kind: 'outcome'\|schemaVersion: style.version" skills/cdp/sdk/video.ts` → :438/:458/:462/:476/:489.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "compileBrief", limit: 3, fields: ["lines"] });
// resolves video.compileBrief @ video.ts:409-509 (single hit)
```

## Verdict
Adopt compiler-inserted opening/closing cards plus keyed splicing for any generated narrative timeline; adapt the 1-based afterAction keying to your index convention (zero-based is the trap); omit header embedding only if your renderer can read the style source directly — then you lose free compile/render drift detection.
