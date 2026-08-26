<!-- capsule-v2 -->
# iOS touch scroll lock — how do you stop rubber-band scrolling on iOS while keeping inner lists scrollable?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What exact touch-event rules prevent background scroll on iOS without breaking scrollable containers inside the overlay?

## handleIOSLocking ScrollLockStep
**Path/Symbol:** `packages/@headlessui-react/src/hooks/document-overflow/handle-ios-locking.ts:10-182`; gated by `platform.ts:isIOS()` (iPhone OR Mac-with-touch-points).
**Signature:** `handleIOSLocking(): ScrollLockStep<ContainerMetadata>` where meta is `{ containers: (() => HTMLElement[])[] }` — returns `{}` (no-op) off iOS.
**Data Shape:** everything registers into the step ctx disposables inside ONE `d.microTask` so body-offset happens after layout settles.

### Decisive source
```ts
// 1. smooth-scroll must die before offsetting the body:
if (window.getComputedStyle(doc.documentElement).scrollBehavior !== 'auto') {
  let _d = disposables()
  _d.style(doc.documentElement, 'scrollBehavior', 'auto')
  d.add(() => d.microTask(() => _d.dispose()))   // restore LATER than our own writes
}
let scrollPosition = window.scrollY ?? window.pageYOffset

// 2. capture <a href="#hash"> clicks whose target lives OUTSIDE allowed containers:
let anchor = e.target.closest('a'); let { hash } = new URL(anchor.href)
let el = doc.querySelector(hash)
if (DOM.isHTMLorSVGElement(el) && !inAllowedContainer(el)) scrollToElement = el

// 3. touchstart: root-container gets overscrollBehavior 'contain', others get touchAction 'none'
// 4. touchmove ({passive:false}) decision ladder:
if (DOM.isHTMLInputElement(e.target)) return                    // range inputs need touch
if (inAllowedContainer(e.target)) {
  let scrollableParent = e.target
  while (scrollableParent.parentElement && scrollableParent.dataset.headlessuiPortal !== '') {
    if (scrollableParent.scrollHeight > scrollableParent.clientHeight ||
        scrollableParent.scrollWidth  > scrollableParent.clientWidth) break   // REAL overflow found
    scrollableParent = scrollableParent.parentElement
  }
  if (scrollableParent.dataset.headlessuiPortal === '') e.preventDefault()    // crawled to portal edge: nothing scrollable => block
} else { e.preventDefault() }                                    // outside allowed containers: always block

// 5. cleanup restores scrollY if it drifted and re-scrolls captured anchors:
if (scrollPosition !== newScrollPosition) window.scrollTo(0, scrollPosition)
if (scrollToElement && scrollToElement.isConnected) scrollToElement.scrollIntoView({ block: 'nearest' })
```

**Flow:** microTask → freeze scroll-behavior → snapshot scrollY + anchor listener → per-touch classify target (allowed-root ⇒ overscroll-contain; disallowed ⇒ touch-action none) → every touchmove either finds a genuinely-overflowing scroller (allow) or preventDefaults at the portal boundary → dispose restores Y position and jumps to any captured hash element.
**Invariant:** the overflow heuristic (`scrollHeight > clientHeight`) is deliberately NOT an `overflow:` CSS check — overscroll-behavior doesn't fire without real overflow; `input[type=range]` must never be blocked; the portal dataset attribute is the crawl STOP marker ("we are always inside a Headless UI Portal"); restoring `scroll-behavior` is delayed one microTask past unlock.
**Probe:** deterministic ladder checks executed against source (range-input early-return, portal-boundary preventDefault, contain-vs-none classification). Direct behavior pinned by dialog.test.tsx open/close suites on jsdom-lite level only — real iOS behavior is source-comment-documented, no device test in repo.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "handleIOSLocking", name_pattern: "^handleIOSLocking$", limit: 5 });
```

## Verdict
Adopt the five-part choreography and the overflow heuristic verbatim for any iOS-targeted modal system; adapt container resolution to your own allowed-list plumbing; omit entirely on non-iOS platforms (the factory already does). Caveat: relies on the `[data-headlessui-portal]` wrapper existing — keep that invariant when porting Portal.
