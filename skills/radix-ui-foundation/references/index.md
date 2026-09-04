<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Radix UI Primitives Foundation

## Use this for
Use when porting headless component-library machinery: trapping or roving focus across portals, stacking overlay layers so Escape and outside-interactions hit only the topmost surface, keeping components mounted during exit animations without a flash, positioning a menu aligned to its trigger's selected item, assembling floating-ui middleware ladders, collecting items in DOM order from a React tree, composing event handlers around `preventDefault`, bridging controlled/uncontrolled state, or synthesizing native form controls for autofill. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./select-item-aligned-positioning.md` — the trigger→selected-item alignment math: min-width mirroring, five-item viewport floor, top/bottom expansion branches, scroll-button reposition latch.
- `./select-typeahead-engine.md` — 1s-decay search buffer, repeated-character normalization, wrap-array forward-only matching with the single-char exclude-current rule.
- `./select-native-form-contract.md` — visually-hidden `<select>` bubble input: no React `value` attribute, prototype-setter dispatch, options-keyed rebuild, empty-value clear-option dedupe.
- `./select-content-keepalive-fragment.md` — items stay mounted in a detached DocumentFragment while closed so native options + selected textValue never go stale.
- `./select-auto-scroll-buttons.md` — visibility-derived edge buttons scrolling one item per 50ms tick (zoom-safe Math.ceil), plus wheel-driven viewport height expansion.
- `./focus-scope-trap-lattice.md` — focusin/focusout reclaim, null-relatedTarget browser bail, MutationObserver body refocus, tabbable TreeWalker approximation, nested-scope pause/resume stack.
- `./presence-exit-animation-fsm.md` — mounted/unmountSuspended/unmounted machine driven by computed animation-name deltas, animationcancel as end-twin, fill-mode forwards flash fix, stable composed refs.
- `./dismissable-layer-stack-arbitration.md` — creation-ordered layer sets, pointer-events arbitration by index comparison, body restore on prop flip, capture-phase Escape for highest layer only.
- `./dismissable-outside-detection.md` — pointerdown-capture sentinel + document listener, deferred click wait for touch/stopPropagation cancellation, six-event interception ledger, shadow-DOM composedPath.
- `./popper-middleware-assembly.md` — fixed-strategy floating-ui ladder offset→shift(limitShift)→flip→size(CSS vars)→arrow→transformOrigin→hide(referenceHidden), callback-ref anchor registration.
- `./roving-focus-tabindex-broker.md` — count-driven group tabIndex, hydration-split dual-effect registration, RTL arrow mirroring, wrapArray loop ladder, shift+Tab exit latch.
- `./collection-document-order-map.md` — OrderedDict keyed by element, sorted by compareDocumentPosition on every mutation, delete-rebuild copy, render-phase shallow-equal data latch.
- `./compose-event-handlers-prevention-gate.md` — original-first invocation with `checkForDefaultPrevented` gate, plus iframe-piercing activeElement descent and aria-activedescendant resolution.
- `./use-controllable-state-ref-latch.md` — controlled-mode onChange fired through an insertion-effect-refreshed ref without owning state; dev-mode controlled↔uncontrolled flip warning.
- `./focus-guards-shared-singleton.md` — module-level guard pair reused across mounts, conditional DOM writes to avoid reflow storms, count-based removal by last unmount.

## Capsule map
- **Select positioning** — `select-item-aligned-positioning`: fixed wrapper sized from border-box geometry; horizontal mirrors trigger width via valueNode/itemText offsets clamped to viewport margins; vertical aligns selectedItem middle to trigger middle with minContentHeight = min(5 items, full height); scroll-button mount re-runs position once (`shouldRepositionRef`); expand-on-scroll arms only after `requestAnimationFrame`.
- **Auto-scroll edges** — `select-auto-scroll-buttons`: visibility-derived up/down buttons (scrollTop>0 / Math.ceil-guarded < maxScroll) run ONE 50ms interval each scrolling a selectedItem height; pointermove re-arms after onItemLeave; wheel inside the viewport expands wrapper height by scrolled amount with bottom-pin compensation; buttons never compress (`flexShrink: 0`).
- **Typeahead** — `select-typeahead-engine`: searchRef decays via self-rescheduling 1000ms timeout; `aaa…` normalizes to `a`; wrapArray rotates candidates after current; single-char searches filter out currentItem so focus always moves.
- **Native form bridge** — `select-native-form-contract`: BubbleInput sets value through `HTMLSelectElement.prototype.value` descriptor then dispatches bubbling `change`; keyed by joined option values so React rebuilds it when options change; synthetic placeholder `<option value="">` suppressed when an Item already carries empty value.
- **Closed-state data** — `select-content-keepalive-fragment`: Presence render-prop branches between the positioned impl and a detached DocumentFragment portal; item effects keep native options + selected textValue fresh while closed; SSR-safe null until first layout effect; aria-controls contract pinned by upstream tests.
- **Focus trap** — `focus-scope-trap-lattice`: document focusin/out handlers reclaim to lastFocusedElementRef; null relatedTarget (tab/window switch, Chrome removed-node) deliberately ignored; MutationObserver refocuses container when focused node removed; tabbable = TreeWalker over `tabIndex >= 0` ignoring positive-tabIndex ordering; unmount autofocus delayed `setTimeout(0)` for React #17894.
- **Presence FSM** — `presence-exit-animation-fsm`: three states; layout effect compares prev vs current animationName to choose ANIMATION_OUT vs instant UNMOUNT; `animationcancel` shares the END handler gated by CSS.escape'd name equality; fill-mode 'forwards' pinned then restored via setTimeout to kill the React-18 flash; useStableComposedRefs keeps ref identity to avoid React 19 update loops.
- **Layer stack** — `dismissable-layer-stack-arbitration`: two context Sets give creation order; `pointerEvents` enabled iff index ≥ index of highest pointer-disabling layer; disabled-set membership re-evaluated on prop change (#3645); Escape listened capture-phase but ONLY by the highest layer; stack effects split so prop flips don't reorder creation order.
- **Outside detection** — `dismissable-outside-detection`: capture/bubble sentinels distinguish React-tree-inside from DOM-inside; primary-button outside-down can defer dismissal to `click` (touch 350ms + stopPropagation interceptors), tracked per-event-type in a Map ledger; pointerdown registered inside setTimeout(0) so opener clicks don't self-dismiss; shadow hosts pierced via `composedPath()`.
- **Popper** — `popper-middleware-assembly`: strategy fixed; middleware ladder order is load-bearing (offset(+arrowHeight) → shift w/ limitShift for sticky=partial → flip → size writing four --radix-popper-* vars → arrow → transformOrigin → hide referenceHidden); hide middleware alone falls back to Floating-UI clipping ancestors; content kept off-page via translate(0,-200%) until positioned; anchor set from commit-phase callback ref not effect (#3858).
- **Roving tabindex** — `roving-focus-tabindex-broker`: group tabIndex = -1 while focusableItemsCount === 0 else 0; items register via layout-effect post-hydration / passive pre-hydration (#3077); arrows mirrored for RTL; loop uses wrapArray else slice; shift+Tab sets isTabbingBackOut which drops group tabIndex to -1.
- **Collections** — `collection-document-order-map`: itemMap is an OrderedDict keyed BY ELEMENT; every add/update sorts via compareDocumentPosition; deletion returns `new OrderedDict(map)` (fresh identity); item data latched render-phase behind shallowEqual; consumer reads map directly (no subscription).
- **Handler composition** — `compose-event-handlers-prevention-gate`: run original then ours unless ours is defaultPrevented-sensitive and event.defaultPrevented; `getActiveElement` descends into iframes and resolves aria-activedescendant ids.
- **Controlled bridge** — `use-controllable-state-ref-latch`: controlled setValue computes nextValue against prop and fires onChangeRef directly (state stays prop-owned); uncontrolled path defers onChange to an effect comparing prevValueRef; onChangeRef refreshed in useInsertionEffect so callbacks never go stale mid-render-commit.
- **Focus guards** — `focus-guards-shared-singleton`: one start/end span pair at document.body edges shared by all consumers; insertAdjacentElement skipped when invariant already holds (avoids forced reflow under sibling layout readers); count tracks consumers; last unmount removes pair and nulls cache.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. High-value pass-2 targets: `packages/react/menu/src/menu.tsx` (1,000+L shared menu kernel: typed item registration, focus intents, sub-menu trigger choreography), `packages/react/toast/src/` (viewport swipe/pause lifetime FSM + guarantee timers), `packages/react/slider/src/slider.tsx` (vertical/horizontal thumb math + collection reuse), `packages/core/number/src/index.ts` (decimal-clamp stepping used by slider), `packages/react/use-rect/src/use-rect.tsx` + `packages/core/rect/` (ResizeObserver observation contract feeding popper anchors), `packages/react/one-time-password-field/src/` (input event synthesis for autofill), `packages/react/form/src/form.tsx` (form-association id plumbing consumed by BubbleInput). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
radix-ui/primitives (MIT), `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae` (= base_sha, first pass, zero drift; worktree clean, origin/main verified 0 commits ahead); Codebase Memory project `ext-ui-radix-ui` (ready, root `$REFERENCE_ROOT/external/ui-radix-ui`, branch main@same sha, 5,333 nodes / 12,615 edges, FULL mode, generation 2026-08-23T11:12:13Z generation_matches=true; parse_partial ×11 = storybook stories/CSS + `core/primitive/src/index.ts` barrel line 2 — none cited; not_indexed ×4 images/favicon BY DESIGN).

## Full view (memory graph)
Revalidate `ext-ui-radix-ui` before porting: run `index_status --project ext-ui-radix-ui --verbose`, `check_index_coverage` (stdin JSON), `search_graph`, `trace_path`, `get_code_snippet`. Root `$REFERENCE_ROOT/external/ui-radix-ui`, branch `main@f7ecd5ab`, 5,333 nodes / 12,615 edges. All 11 cited source paths reported `no_recorded_issue` + `metadata_match` on check_index_coverage at this pin. Graph retrieval verified live: `SelectItemAlignedPosition` :935-1148, `useTypeaheadSearch` :1857-1887 / `findNextItem` :1906-1921, `SelectBubbleInput` :1763-1845, `FocusScope` :57-239 (+ branch registry :258-307), `usePresence` :29-187 / `useStateMachine` :12-20, `DismissableLayer` :71-246 / `usePointerDownOutside` :308-494, `PopperContent` :182-358 / `transformOrigin` :430-465, `RovingFocusGroupImpl` :110-208 / `getFocusIntent` :366-375, `createCollection` :30-261 / `sortByDocumentPosition` :284-293, `composeEventHandlers` :11-23 / `getActiveElement` :45-71. Direct-test coverage is strong upstream: `select.test.tsx` (form-reset matrix :272-390, keys-from-descendants :196, ref stability :238, clear-value #2706 suite :77-145), `focus-scope.test.tsx`, `presence.test.tsx` (ref-loop regressions #3664 :10/:25), `dismissable-layer.test.tsx` (:68-280 incl. defer/shadow-tree/branch cases), `popper.test.tsx`, `roving-focus-group.test.tsx`, `focus-guards.test.tsx`. Runner note: probes executed as deterministic byte-exact grep/sed checks against cited sources (53-probe battery scratch-uix1/probe_battery.py 53/53 GREEN); jest not run in the inspo clone (no installed workspace deps).

## Boundaries
Adopt the pure contracts: focus-trap reclaim semantics, layer-stack pointer-events arbitration, animation-name-driven presence FSM, document-position-ordered collections, prevention-aware handler composition, controlled-state ref latching. Adapt host-specific details: floating-ui middleware parameters, react-remove-scroll/aria-hidden third-party integrations, CSS custom-property naming, scoped-context wiring (`__scope*`) if your library uses plain contexts. Omit source-specific behavior: storybook stories, SSR-testing app, the deprecated `collection-legacy.tsx` API, and version-specific React workarounds you can drop (React ≤18 `getElementRef` DEV-warning dance still needed only for older React).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`collection-document-order-map.md`](./collection-document-order-map.md)
- [`compose-event-handlers-prevention-gate.md`](./compose-event-handlers-prevention-gate.md)
- [`dismissable-layer-stack-arbitration.md`](./dismissable-layer-stack-arbitration.md)
- [`dismissable-outside-detection.md`](./dismissable-outside-detection.md)
- [`focus-guards-shared-singleton.md`](./focus-guards-shared-singleton.md)
- [`focus-scope-trap-lattice.md`](./focus-scope-trap-lattice.md)
- [`popper-middleware-assembly.md`](./popper-middleware-assembly.md)
- [`presence-exit-animation-fsm.md`](./presence-exit-animation-fsm.md)
- [`roving-focus-tabindex-broker.md`](./roving-focus-tabindex-broker.md)
- [`select-auto-scroll-buttons.md`](./select-auto-scroll-buttons.md)
- [`select-content-keepalive-fragment.md`](./select-content-keepalive-fragment.md)
- [`select-item-aligned-positioning.md`](./select-item-aligned-positioning.md)
- [`select-native-form-contract.md`](./select-native-form-contract.md)
- [`select-typeahead-engine.md`](./select-typeahead-engine.md)
- [`use-controllable-state-ref-latch.md`](./use-controllable-state-ref-latch.md)
