<!-- capsule-v2 -->
# Trigger spec grammar — how does an `hx-trigger` string become a specification object, and where are the sharp edges?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is the exact token grammar of `hx-trigger` (events, modifiers, filters, polling) and which inputs silently degrade instead of erroring?

## parseAndCacheTrigger: tokenizer → per-spec option loop
**Path/Symbol:** `src/htmx.js:parseAndCacheTrigger` (:2234-2321) over `tokenizeString` (:2103-2132), `maybeGenerateConditional` (:2155-2195), `consumeUntil` (:2202-2208), `consumeCSSSelector` (:2214-2224); cache wiring in `getTriggerSpecs` (:2327-2346).
**Signature:** `function parseAndCacheTrigger(elt, explicitTrigger, cache)` → `HtmxTriggerSpecification[]`; tokenizer `function tokenizeString(str)` → `string[]`.
**Data Shape:** Spec fields: `{trigger, pollInterval?, eventFilter?, changed?, once?, consume?, delay?, from?, target?, throttle?, queue?, root?, threshold?}`. Intervals go through `parseInterval` (`s`=×1000, `ms`=×1, bare=parseFloat, `NaN→undefined`). The optional `cache` is any object keyed by the raw trigger string (`config.triggerSpecsCache`).

### Decisive source
```js
const trigger = consumeUntil(tokens, /[,\[\s]/)
if (trigger !== '') {
  if (trigger === 'every') {
    const every = { trigger: 'every' }
    every.pollInterval = parseInterval(consumeUntil(tokens, /[,\[\s]/))
    var eventFilter = maybeGenerateConditional(elt, tokens, 'event')
    if (eventFilter) { every.eventFilter = eventFilter }
    triggerSpecs.push(every)
  } else {
    const triggerSpec = { trigger }
    ... // option loop:
    //   changed / once / consume           → boolean flags
    //   delay: throttle:                   → parseInterval(consumeUntil(WHITESPACE_OR_COMMA))
    //   from:                              → consumeCSSSelector; bare closest|find|next|previous
    //                                          consumes one more selector ('next'/'previous' may be selector-less)
    //   target: root: threshold:           → selector / parseFloat'd later by intersect handling
    //   queue:                             → plain word (first|all|last)
    //   anything else                      → triggerErrorEvent(elt,'htmx:syntax:error')
  }
}
if (tokens.length === initialLength) { /* zero progress ⇒ htmx:syntax:error */ }
```

Tokenizer facts a porter must keep: symbol chars are `[_$a-zA-Z]` + `[_$a-zA-Z0-9]`; `"`, `'`, and `/` start STRINGISH tokens consumed to the matching quote with `\` escapes — so `/` inside a trigger is quote-open, not regex. Conditionals `[expr]` become compiled functions via `maybeGenerateConditional`: relative references become `((event.X) ? (event.X) : (window.X))`; empty brackets compile to `true`. The function carries `.source` for error reporting; eval is gated by `htmx.config.allowEval` through `maybeEval`.

**Flow:** tokenize whole attribute → loop: skip ws, read trigger word, branch every-vs-event, parse options until `,`, push spec → repeat while next token is comma.
**Invariant:** Defaults live in `getTriggerSpecs`, NOT the parser: no explicit specs ⇒ form→submit, `input[type=button|submit]`→click, other input/textarea/select→change, everything else→click. Unknown tokens fire `htmx:syntax:error` on the element and parsing continues. SHARP EDGE (executed headless): inside `hx-trigger`, combined selectors are only `(...)`/`{...}` (`COMBINED_SELECTOR_START = /[{(]/`) — `from:closest <div/>` does NOT parse as chevron-selector; the `/` opens a stringish token that swallows the rest of the spec and emits `htmx:syntax:error`. Chevron selectors belong to hx-target/hx-indicator values (`querySelectorAllExt`), not to trigger modifiers.

**Probe:** Grammar table pinned by `test/attributes/hx-trigger.js` "parses spec strings" (:285+, e.g. `'event throttle:1s, foo' → [{trigger:'event',throttle:1000},{trigger:'foo'}]`, `'every 0ms' → [{trigger:'every',pollInterval:0}]`); cache behavior "uses trigger specs cache if defined" :1290. Tokenizer battery: `test/core/tokenizer.js` "tokenizes properly" :19 (quotes-with-commas cases). Executed headless (Node vm): `click`→`[{trigger:'click'}]`; `every 2s`→pollInterval 2000; `delay:500ms`→500; `input changed once`→flags; `from:(body)`→`from:'body'`; `from:{p .btn}`→`'p .btn'`; `target:#x`; `queue all`; `intersect root:#sc threshold:0.3`→root+threshold strings; filter compiles to eventFilter fn.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "parseAndCacheTrigger trigger specification tokens", limit: 4 });
```
(rank-1 `src.htmx.parseAndCacheTrigger src/htmx.js 2234-2321`)

## Verdict
Adopt the two-layer design (dumb tokenizer + option loop with syntax-error events) and the default-trigger ladder in getTriggerSpecs. Adapt interval units to your host's parser but keep `0ms ⇒ 0` (pollInterval 0 still polls). Omit the `cache` parameter only if you accept re-parsing costs; note it exists precisely because spec parsing allocates closures per element. Coverage caveat: runner blocked (no node_modules); expectations above were executed headless against source at the pinned commit plus repo test tables.
