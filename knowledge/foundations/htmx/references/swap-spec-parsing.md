<!-- capsule-v2 -->
# Swap specification parsing — how does an hx-swap value decompose into style + modifiers, and what tolerates garbage?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is the modifier grammar of hx-swap (`swap: settle: transition: ignoreTitle: scroll: show: focus-scroll:`), which token becomes the swapStyle, and how do malformed specs behave?

## getSwapSpecification: whitespace-split, first-positional style
**Path/Symbol:** `src/htmx.js:getSwapSpecification` (:3764-3815); defaults from config; boosted override; scroll/show target-splitting with LAST-colon semantics.
**Signature:** `function getSwapSpecification(elt, swapInfoOverride)` → `{swapStyle, swapDelay, settleDelay, transition?, ignoreTitle?, scroll?, scrollTarget?, show?, showTarget?, focusScroll?}`. Defaults: config.defaultSwapStyle/'innerHTML', defaultSwapDelay 0, defaultSettleDelay 20; boosted elements FORCE innerHTML and add `show:'top'` when scrollIntoViewOnBoost and not an anchor link.
**Data Shape:** Tokens are splitOnWhitespace of the closest-inherited hx-swap value. Modifier prefixes win by `indexOf(... ) === 0` order in the loop: swap:, settle:, transition:, ignoreTitle:, scroll:, show:, focus-scroll:. A token matching NO prefix is taken as the STYLE only if it sits at position 0 (`i == 0`), otherwise it's logged as "Unknown modifier in hx-swap" and skipped.

### Decisive source
```js
} else if (value.indexOf('scroll:') === 0) {
  const scrollSpec = value.slice(7)
  var splitSpec = scrollSpec.split(':')
  const scrollVal = splitSpec.pop()          // DIRECTION is the last segment...
  var selectorVal = splitSpec.length > 0 ? splitSpec.join(':') : null  // ...selector is everything before it
  swapSpec.scroll = scrollVal
  swapSpec.scrollTarget = selectorVal
}
```

**Flow:** read attribute → split → per-token classify → unknown non-first tokens tolerated (test asserts `'innerHTML nonsense settle:11 swap:10'` still yields settleDelay 11 — even multiple spaces around the junk) → return spec.
**Invariant:** The grammar is DIRECTION-LAST: `show:#t:bottom` means show='bottom' on '#t'; `show:window:bottom` maps target 'window'→body at consumption time (updateScrollState). Bare numbers for swap:/settle: pass through parseInterval (unitless = ms). `transition:true/false` and `ignoreTitle:true/false` parse strict equality after slicing. Because style detection requires position 0, `'swap:10'` alone keeps innerHTML style WITH a delay — modifier-only strings are legal.
**Flow:** HX-Reswap headers and htmx.ajax `swap:` context feed the SAME parser through swapInfoOverride.

**Probe:** Authoritative table `test/attributes/hx-swap.js` "properly parses various swap specifications" :241-289 (~35 assertions: unitless/ms/s units, zero values, modifier-only strings, order independence `'settle:11 swap:10'`, junk tolerance incl. extra spaces). Direction-last family: scroll:top :359, show:top :407, show:window:bottom :439, focus-scroll:true :454. Executed headless (Node vm): defaults S1 `{swapStyle:'innerHTML',swapDelay:0,settleDelay:20}`; S2 outerHTML+delays; S3 `show:bottom:#t` → `{show:'#t',showTarget:'bottom'}` proving direction-last; S4 transition/ignoreTitle flags.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "getSwapSpecification swap settle delay scroll show modifiers", limit: 5 });
```
(companion rank-1: getSwapSpecification resolves via "swapWithStyle"-adjacent queries; direct symbol reachable at 3764-3815)

## Verdict
Adopt the positional-style rule and direction-last selector parsing exactly — both are user-visible syntax. Adapt unitless-interval handling to your host's duration type. Omit nothing: junk tolerance IS the spec (real pages carry typos).
