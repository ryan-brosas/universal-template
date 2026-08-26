<!-- capsule-v2 -->
# Revealed-text reconstruction — how can an evidence video show what was really typed while masked keystrokes stay unrecoverable?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the flag-veto ladder between the recorder and the video compiler that lets `showTyping: true` render original typed text for proven-safe fields while making masked or password input impossible to reveal?

## Capture-time mask flags are the compile-time veto; projection sanitizers re-truncate everything else
**Path/Symbol:** `skills/cdp/sdk/video.ts:loadRevealedText` (:515-530), showTyping gate in `compileAction` (:352-364), `safeText`/`safeLabel` (:532-544), `SENSITIVE` (:53), `TYPE_HELPERS` (:61); capture-layer counterpart `recording.ts` text gate (:417-449, contract in recording-privacy-scrub).
**Signature:** `loadRevealedText(eventsPath: string): Map<number, string>` keyed by the event's ONE-based JSONL line number; consumed as `compileBrief(summary, brief, style?, revealedText = new Map())` → per beat `text: showTyping ? revealedText.get(sourceLine) : '••••••'`.
**Data Shape:** admission requires ALL of: helper ∈ TYPE_HELPERS (`type_text|fill|fill_input`) ∧ `input !== 'password'` ∧ `password !== true` ∧ `textRedacted !== true` ∧ `text != null`. Every failure mode at capture writes the literal mask `'••••••'` plus `textRedacted: true` (and `password: true` when known).

### Decisive source
```ts
if (TYPE_HELPERS.has(event.helper) && event.input !== 'password' && event.password !== true && event.textRedacted !== true && event.text != null) {
  revealed.set(index + 1, String(event.text));            // :525-526 — the ONLY admission path
}
// compileAction gate:
if (showTyping && event.password) throw new BriefError(`actions[${index}].showTyping cannot reveal a password field`);  // :353
if (showTyping && !revealedText.has(sourceLine)) throw new BriefError(`actions[${index}].showTyping requires the original typed event`); // :355-356
beat.type = { box: …, text: showTyping ? revealedText.get(sourceLine) : '••••••', ...(showTyping ? {} : { redact: true }) };  // :358-362
// projection layer (summary/events fed to the template):
function safeText(event: Json) { if (TYPE_HELPERS.has(event.helper)) return '<typed text hidden>';
  if (event.input === 'password' || event.password === true || SENSITIVE.test(value)) return '<sensitive>';
  return value.slice(0, 120); }                            // :532-538; safeLabel same regex + truncation :540-544
```

**Flow:** at CAPTURE the recorder keeps typed text on disk only when focused-element inspection positively proved non-password; otherwise it writes the mask + redaction flags (recording-privacy-scrub) → at COMPILE the CLI loads `revealedText = loadRevealedText(events.jsonl)` and passes it into `compileBrief` → a beat asking `showTyping: true` must reference an event whose line number is IN that map, else compile fails; password-flagged events throw outright → without explicit reveal, typing renders as `'••••••'` carrying `redact: true` → independently, EVERYTHING projected into the summary/template goes through `safeText`/`safeLabel`: type-helper texts collapse to `<typed text hidden>`, SENSITIVE matches (@, tenant/user/object ids, GUIDs, onmicrosoft.com) become `<sensitive>`, labels truncate at 120 chars.
**Invariant:** (1) FAIL-CLOSED END-TO-END: the capture-time flags ARE the compile-time veto — a masked line can never be revealed later because admission re-checks the same flags from disk; there is no code path from `'••••••'` back to plaintext. (2) Reveal is OPT-IN and PER-BEAT via `sourceLine`, never bulk. (3) The ladder is layered defense: even revealed beats pass through privacy review completeness (every used frame reviewed) before export, and the projection layer still masks/truncates everything AROUND the beats — but note honestly: sensitive-yet-non-password content in an explicitly revealed field renders by design; the guarantee is specifically "no masked/password text can render". (4) Line-number keying ties reveals to exact recorded events — a brief cannot reveal event N's text onto beat M.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts`: default typing asserts `{text:'••••••', redact:true}` (:58-62); `'typing requires explicit reveal…'` drives `loadRevealedText` → `compileBrief(..., revealed)` → `beats[2].type.text === 'private draft'` and rejects unsafe routes with BriefError (:70-83). Deterministic greps: `grep -n "export function loadRevealedText\|showTyping cannot reveal a password\|const SENSITIVE" skills/cdp/sdk/video.ts` (:515, :353, :53). Suite executed GREEN this pass (see work record verification.md).
**Coverage caveat:** edit-brief-validation covers the compile-gate side of `showTyping`; this capsule adds the uncited reconstruction half (`loadRevealedText`/`safeText`/`safeLabel`) and the end-to-end veto chain.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "loadRevealedText", limit: 3, fields: ["signature", "name", "file"] });
// resolves browser-harness-js.skills.cdp.sdk.video.loadRevealedText @ video.ts:515-530  (executed this pass)
```

## Verdict
Adopt the flag-veto pattern for ANY pipeline where a capture layer and a rendering layer share sensitive data: the producer's fail-closed flags must be re-checked at every downstream admission point, not trusted forward. Adapt the SENSITIVE regex to your domain's identifiers. Omit nothing here if your evidence files can ever contain human-typed credentials.
