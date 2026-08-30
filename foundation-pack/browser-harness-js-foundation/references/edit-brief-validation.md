<!-- capsule-v2 -->
# Edit-brief validation ladder — what makes a video composition compile, and which editorial rules are ENFORCED rather than suggested?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Which brief fields are rejected outright, and how does the compiler stop an LLM from producing a 3-minute slideshow?

## Unknown-key rejection, viewport pinning, narration cadence gates, duration budget with remediation text
**Path/Symbol:** `skills/cdp/sdk/video.ts:compileBrief` (:409-509), `compileAction` (:287-377), `validateNarrationCadence` (:262-285), `durationBudget` (:240-246), `addRawToCardHolds` (:248-260), `validatePrivacy` (:379-407).
**Signature:** `compileBrief(summary: Json, brief: Json, style?: Json, revealedText?: Map<number, string>): Json` — throws `BriefError` on every violation.
**Data Shape:** allowed keys per object are CLOSED sets (`BRIEF_KEYS`, `ACTION_KEYS`, `EXPLANATION_KEYS`, `PRIVACY_KEYS`, `REDACTION_KEYS`); plan = exactly 2–5 strings; outcomes = 1–5; narration ≤ 7 words; events are ONE-based indices into recording-summary.json; chapters ZERO-based.

### Decisive source
```ts
function rejectUnknown(value: Json, allowed: Set<string>, where: string): void {
  const unknown = Object.keys(value).filter(key => !allowed.has(key)).sort();
  if (unknown.length) throw new BriefError(`${where} has unsupported field(s): ${unknown.join(', ')}`);
}
...
if (segment.length >= 3 && cues.length > Math.ceil(segment.length / 2)) {
  throw new BriefError('narration is sticky: set it only when the thought changes, then omit it while 2–3 screenshots advance underneath');
}
let consecutive = 0;
for (const beat of segment) { consecutive = beat.narration ? consecutive + 1 : 0;
  if (consecutive >= 3) throw new BriefError('three consecutive actions change narration; ...'); }
```
and the budget gate:
```ts
const duration = round(beats.reduce((sum, b) => sum + Number(b.dur), 0));
if (duration > budget + 0.001) throw new BriefError(`compiled video is ${duration}s; house-style budget is ${budget}. Shorten card copy, remove redundant actions, or set narration only when the thought changes; viewers can pause for detail`);
```

**Flow:** reject unknown keys at every level → validate task/plan/outcomes shapes → first action's event pins the composition VIEWPORT (±2px tolerance enforced per action via `requireMatchingViewport` — mixed viewports must be split/normalized first) → per action: one-based event must have a frame, chapter indexes the plan, `route` must be SEMANTIC (regex `ROUTE_UNSAFE` rejects raw URLs/@/UUIDs), clicks require captured cursor coords, typing requires a captured box and (for `showTyping`) the original non-password event in `revealedText` → splice explanation cards → cadence gates → raw→card transition holds (+0.55s each) → duration budget = base 22s + extras capped at 32s → privacy review completeness (every used frame reviewed; no unused redactions).
**Invariant:** (1) The house style is CODE: pacing numbers live in HOUSE_STYLE and the compiler enforces them — an LLM cannot ship a rambling cut because the compile fails with remediation advice. (2) Privacy is structural: `reviewedFrames` must cover every frame the composition uses and `redact` may only list used frames. (3) Password reveal is impossible by construction — `showTyping` on a password event throws.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts`: compile shape assertions (:46-68), explicit-reveal success vs unsafe-route rejection (:70-83).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "compileBrief", limit: 3, fields: ["signature", "name", "file"] });
// resolves video.compileBrief @ video.ts:409-509
```

## Verdict
Adopt closed-key rejection + machine-enforced editorial budgets whenever LLM-authored JSON drives rendered output; adapt the pacing constants and word caps to your medium; omit the route-safety regex only if your labels can never contain URLs/identities.
