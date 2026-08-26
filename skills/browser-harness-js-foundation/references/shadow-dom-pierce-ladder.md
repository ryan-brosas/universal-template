<!-- capsule-v2 -->
# shadow-dom-pierce-ladder — how do you reach elements inside shadow roots, and which parts are unreachable?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What pierces open shadow roots, what crosses closed ones, and where does slotted content actually live?

## Pierce ladder + light-DOM rule
**Path/Symbol:** `skills/cdp/interaction-skills/shadow-dom.md` whole doc — coordinates-first (:5–7), CDP path (:9–22), JS walk (:24–55), value-set inside shadow (:57–71), Traps (:75–80).
**Signature:** CDP: `DOM.querySelector({nodeId, selector: 'my-button >>> .inner-label'})` — the `>>>` combinator pierces open shadow boundaries on recent Chrome (`pierceShadow: true` historically accepted); portable JS: generator stack-walk pushing `node.shadowRoot.children`. Value set: focus → `.value = …` → `dispatchEvent(new Event('input', { bubbles: true, composed: true }))`.
**Data Shape:** closed roots (`{mode:'closed'}`) unreachable from JS — rare (password managers, some Google components) → coordinate clicks + insertText are the only path. Slot content lives in the LIGHT DOM (`host.children`), NOT host.shadowRoot.children. Element screenshots via getBoxModel work once you hold a nodeId.

### Decisive source
```md
- **Closed shadow roots** (`{ mode: 'closed' }`) cannot be walked from JS.
  Fall back to coordinate clicks + `Input.insertText`. Closed roots are rare
  — usually only password managers and some Google components.
- **`slot` content lives in the light DOM**, not the shadow root.
```

**Flow:** see it in a screenshot? → coordinate click (avoids piercing entirely) → need DOM? → `>>>` selector or recursive shadowRoot walk → set value with composed input event (many web components listen on the HOST, not the internal input).
**Invariant:** `composed: true` is load-bearing for cross-boundary event propagation; walking shadowRoot.children finds nothing for slotted content — checking the wrong tree is a silent miss. Closed-root detection should trigger the coordinate fallback immediately rather than deeper selector attempts.
**Probe:** `grep -cF 'pierceShadow' skills/cdp/interaction-skills/shadow-dom.md` → 4; `grep -cF '>>>' <same>` → 2; `grep -cF 'cannot be walked from JS' <same>` → 1; Static probe (anchored at the `skills/cdp/interaction-skills/` dir): `grep -cF '`composed: true` on the event lets it cross shadow boundaries' shadow-dom.md` → 1; `grep -cF '**`slot` content lives in the light DOM**, not the shadow root' shadow-dom.md` → 1. NOTE: never write these patterns with escaped backticks (`\``) inside single quotes — bash treats the backslashes literally and the probe matches zero (shipped that way once; repaired after live execution caught it).
**Retrieve:** search_code --project browser-harness-js --pattern "shadowRoot" (Module node resolves line-exact).

## Verdict
Adopt coordinates-first then >>>/walk ladder and the slot-in-light-DOM rule as portable knowledge. Adapt the value-set event per component library. Omit ::part()/::slotted notes (CSS-only concern).
