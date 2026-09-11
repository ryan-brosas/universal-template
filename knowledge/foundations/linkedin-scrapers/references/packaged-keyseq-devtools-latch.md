<!-- capsule-v2 -->
# packaged-keyseq-devtools-latch — how do I ship DevTools/recovery hooks in a PACKAGED Electron app so end users can never trigger them, yet field support still can?

**Source:** linked-helper-extract **NO LICENSE — learn-only, patterns recorded, zero code copied**; Codebase Memory `linked-helper-extract-dist` (root `app-src/dist`, minified single-line files — spans collapse to whole-file; symbol retrieval is the anchor). **Question:** what is the correct gating pattern for debug backdoors in a production desktop launcher?

## before-input-event sequence latch (packaged vs dev branches)
**Path/Symbol:** `dist/Window.js:Window.constructor` — two `webContents.on('before-input-event')` registrations selected by `electron.app.isPackaged`.
**Signature:** handler `(event, input) => void` where `input = {type:'keyDown', key, control, shift, isAutoRepeat}`; helpers invoked via globals: `global.autoRestartHandler()`, `global.restoreMenuHandler()`, `global.unlockHandler()`; `openDevTools({mode:'detach', activate:true})`.
**Data Shape:** latch state machine per Window instance: `entered` bool + `seq` string; magic words `"launcher"` (DevTools), `"auto"` (auto-restart), `"bbb"` (restore menu), `"unlock"` (license/feature unlock).

### Decisive source
```js
if (app.isPackaged) {
  webContents.on('before-input-event', (e, input) => {
    if (!input.isAutoRepeat && input.type === 'keyDown') {
      // chord openers consume the event and RESET the buffer
      if (input.control && input.shift && (input.key === 'i' || input.key === 'I')) {
        entered = true; seq = ''; e.preventDefault();
      } else if (input.control && input.shift && (input.key === 'u' || …'U')) { entered = true; seq=''; e.preventDefault(); }
      else if (input.control && input.shift && (input.key === 'b' || …'B')) { entered=true; seq=''; e.preventDefault(); }
      else if (entered) {
        seq += input.key;
        if ('launcher'.startsWith(seq)) {                    // PREFIX match keeps the latch alive
          e.preventDefault();
          if (seq.length === 8 || seq === 'launcher') {       // full word → fire once, re-arm
            entered = false; seq = '';
            webContents.openDevTools({ mode: 'detach', activate: true });
          }
        }
        else if ('auto'.startsWith(seq))   { /* complete ⇒ global.autoRestartHandler() */ }
        else if ('bbb'.startsWith(seq))    { /* complete ⇒ global.restoreMenuHandler() */ }
        else if ('unlock'.startsWith(seq)) { /* complete ⇒ global.unlockHandler() */ }
        else { entered = false; seq = ''; }                   // ANY off-path keystroke kills the latch
      }
    }
  });
} else {
  // DEV build: same chords fire IMMEDIATELY, no word completion, no latch
  if (input.control && input.shift && key==='i') { openDevTools({…}); global.unlockHandler(); }
  else if (…'u') global.autoRestartHandler(); else if (…'b') global.restoreMenuHandler();
}
```

**Flow:** packaged app: user presses Ctrl+Shift+I/U/B (chord opener — consumed) → subsequent plain keystrokes append to `seq`; while any magic word remains a PREFIX of `seq` the latch stays armed (wrong-but-prefix keys are swallowed); completing a word fires its handler exactly once and resets the buffer; any non-prefix key disarms silently. Dev app: the same three chords trigger handlers instantly with no sequence entry.
**Invariant:** in packaged builds NOTHING fires from a single chord — only the full typed word completes an action, and `e.preventDefault()` on opener+matching keys hides the shortcut from the page; `!input.isAutoRepeat` makes held keys emit one event (no autorefill of `seq`); handlers hang off GLOBALS assigned elsewhere, so this window layer stays decoupled from implementation and the unlock surface is testable/replaceable.
**Probe:** no public tests (proprietary dist extract) — coverage caveat recorded. Byte-exact probes anchored at `linked-helper-extract/linked-helper-extract/app-src/dist` (tree is NESTED one level inside the extract dir — the bare `linked-helper-extract/app-src` form does not resolve): `grep -c "startsWith(seq)" Window.js` ⇒ 4; `grep -c "'launcher'" Window.js` ⇒ 2; `grep -c 'openDevTools' Window.js` ⇒ 2 (packaged branch + dev branch); `grep -c 'before-input-event' Window.js` ⇒ 2; `grep -c 'isAutoRepeat' Window.js` ⇒ 2 (one per registration); `grep -o "input.control && input.shift" Window.js | wc -l` ⇒ 6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linked-helper-extract-dist", query: "Window before-input-event", limit: 5 });
// rank#1/#2: Window.Window.constructor (11-117) + getBrowserWindow (118-120), Window.js
```

## Verdict
Adopt the pattern: feature-gate debug surfaces behind multi-keyword typed sequences that are prefix-matched and self-disarming, keep dev builds instant, route actions through injectable globals. Adapt the specific chords/magic words. Omit nothing conceptually. **No-license repo: patterns only, zero code copied.**
