<!-- capsule-v2 -->
# Per-beat page-context probe — how do you attach trustworthy page state to every recorded action when the wire call itself is the untrusted input?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How does an action recorder enrich each wire-level event with real page state (URL, viewport, focused field) it can later trust for privacy decisions, without trusting the caller?

## CONTEXT_EXPRESSION evaluated in-page on the action's own sessionId, merged over event details
**Path/Symbol:** `skills/cdp/sdk/recording.ts:CONTEXT_EXPRESSION` (:46-63), consumed by `RecordingManager.capture` (:427-449).
**Signature:** `const CONTEXT_EXPRESSION: string` (String.raw IIFE) · `capture(...)` runs `session._call('Runtime.evaluate', { expression: CONTEXT_EXPRESSION, returnByValue: true }, { sessionId })`.
**Data Shape:** `PageContext = { url?, title?, w?, h?, sx?, sy?, dpr?, box?: {x,y,w,h}, input? }` — `url/title/w/h/sx/sy/dpr` always present; `box`+`input` only when a focused element exists that is neither `<body>` nor `<html>`.

### Decisive source
```ts
const element = document.activeElement;
if (element && element !== document.body && element !== document.documentElement) {
  const rect = element.getBoundingClientRect();
  if (rect.width || rect.height) out.box = { x: rect.x, y: rect.y, w: rect.width, h: rect.height };
  out.input = String(element.type || element.tagName || '').toLowerCase();
}
...
let context: PageContext = {};
try {
  const response = await this.session._call('Runtime.evaluate', { expression: CONTEXT_EXPRESSION, returnByValue: true }, { sessionId });
  context = response.result?.value ?? {};
  Object.assign(event, context);        // page state OVERWRITES what the call details claimed
} catch { /* The target may be navigating or closing. */ }

if (typeof event.url === 'string') event.url = scrubUrl(event.url);
```

**Flow:** classify the raw CDP call → wait the classified settle delay (`delayMs`) → evaluate the context IIFE **in the same target/sessionId the action fired on**, after the action so post-click focus is observed → merge context over the event (`Object.assign`, page wins) → scrub any URL-shaped value the merge introduced → only then decide typing admission from `context.input` → append one 0600 JSONL line. Probe failure degrades to `{}`, which forces the typing mask downstream.
**Invariant:** THE PAGE IS THE WITNESS, NOT THE CALLER — evidence fields and privacy admissions come from a fresh in-page observation on the action's own session, never from parameters the producing code passed. Two consequences a porter must keep: (1) `input` is set even for a zero-size rect while `box` requires visible width/height (an invisible-but-focused input still classifies as an input); (2) the probe's own `location.href` is NOT trusted raw — it re-enters `scrubUrl` after the merge. The identical evaluation serves two masters: evidence enrichment and the positive-proof typing gate.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts`: `'recorder masks password text and scrubs credential URLs'` (:106-142) drives `RecordingManager.start/observe/stop` against a mock session whose `Runtime.evaluate` returns `{input:'password', url:'https://alice:pw@…?code=…#oauth-state'}` and pins mask flags + exact scrubbed URL; `'typed text fails closed when focused-element inspection fails'` (:145-175) makes `Runtime.evaluate` throw and asserts the plaintext NEVER reaches events.jsonl. Suite executed GREEN at this pin (17/17, pass 5).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "CONTEXT_EXPRESSION", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 5: resolves browser-harness-js.skills.cdp.sdk.recording.CONTEXT_EXPRESSION @ recording.ts:46-63 (Variable, 1 usage edge).
```

## Verdict
Adopt the inverted trust chain (page proves, wire claims) plus the always-fields/conditional-box/input split of the probe for any recorder that must later justify privacy decisions from its own evidence; adapt the collected field set to your evidence schema; omit nothing from the fail-closed coupling — dropping the probe silently converts every typed event into a mask decision made with no witness. Caveat: `recording.ts` is fully graph-indexed (coverage no_recorded_issue + metadata_match, gen matches) but behavior here rests on mock-session tests, not live-browser capture; treat the delay constants (90–500ms by helper class) as adapt-per-environment.
