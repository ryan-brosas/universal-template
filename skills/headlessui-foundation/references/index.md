<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Headless UI: headless primitive contracts

## Use this for
Use when building or porting unstyled accessible components (Dialog, Popover, Menu, Listbox, Combobox): focus trapping and tab direction, focusable-element enumeration order, outside-click with pointer/touch/iframe disambiguation, cross-component "top layer" arbitration, marking the rest of the page inert, document scroll locking incl. iOS touch rules and scrollbar compensation, nested portal registration, DOM-order-safe option registries and typeahead, and hoisting hidden form fields into forms. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./focus-in-bitmask-loop.md` — bitmask Focus algebra, wraparound arithmetic, and the try-focus-until-activeElement loop.
- `./focusable-enumeration.md` — selector set, tabIndex sort, Strict-vs-Loose modes, and restore-after-unmount.
- `./focus-trap-guards.md` — sentinel buttons, FocusLock blur redirect, InitialFocus microtask ladder, RestoreFocus from click history.
- `./top-layer-stack-machine.md` — scoped id stacks, push-moves-to-top, isTopLayer enable-window semantics.
- `./inert-others-refcount.md` — sibling-crawl inert marking with refcounted original-value restoration.
- `./outside-click-pointer-pair.md` — pointerdown-target capture vs touchend target, 30px move threshold, iframe blur.
- `./scroll-lock-store.md` — document-keyed PUSH/POP counter, willChange edge detection, lazy meta fold.
- `./ios-touch-scroll-lock.md` — smooth-behavior override, anchor capture, overscroll-contain, portal-root preventDefault ladder.
- `./dialog-wiring-order.md` — Dialog composition stack and the isClosing feature-shutdown window.
- `./open-closed-context.md` — four-bit Open/Closing context and Transition-aware child demotion.
- `./machine-react-glue.md` — abstract Machine with shallowEqual slices and useSyncExternalStoreWithSelector bridging.
- `./listbox-dom-order-registry.md` — pendingShouldSort rAF deferral and active-index re-lookup after re-sort.
- `./listbox-typeahead.md` — rotation-from-active search over sorted options with disabled skipping.
- `./calculate-active-index.md` — disabled-skip navigation returning null/current on failure, never throwing.
- `./form-fields-hoisting.md` — objectToFormEntries key paths and the hoisted-hidden-inputs pattern.
- `./portal-nesting-registration.md` — shared `#headlessui-portal-root`, child `data-headlessui-portal` wrappers, recursive registration.
- `./stable-collection-index.md` — render-side index allocation with effect-release for SSR-stable ordering.
- `./root-containers-resolution.md` — which body-level subtrees count as "outside" and the main-tree probe fallback.
- `./floating-anchor-config.md` — anchor gap/offset/padding CSS-variable→px resolution via probe element.
- `./hidden-element-styles.md` — HiddenFeatures style/aria matrix for guards, sr-only, and display-none markers.
- `./server-handoff-gating.md` — env handoff protocol and React-18 hydration detection suppressing DOM features.
- `./text-value-computation.md` — typeahead text precedence chain and clone-and-strip innerText algorithm.
- `./focus-visible-tracking.md` — global listeners maintaining data-headlessui-focus-visible on <html>.
- `./disposables-scheduler.md` — cancellable rAF/microtask/style-effect bag powering all DOM hooks.
- `./scrollbar-compensation.md` — before/after scrollbar measurement pair preventing layout shift.
- `./active-element-history.md` — global focus-history ring feeding RestoreFocus snapshots.

## Capsule map
- **Focus movement** — `focus-in-bitmask-loop`: seven Focus bits drive direction/startIndex derivation with a do/while that retries until `document.activeElement` confirms; WrapAround is modular arithmetic, no-wrap returns Underflow/Overflow. `focusable-enumeration`: one selector string (test env appends display-none filters), numeric-tabIndex sort with 0→end via MAX_SAFE_INTEGER, Loose mode walks ancestors, `restoreFocusIfNecessary` waits a nextFrame and only restores when current active element fails Strict mode.
- **Focus trap** — `focus-trap-guards`: Hidden Focusable guard buttons before/after fire handleFocus which re-enters with First/Last skipping relatedTarget+fallback; onBlur redirects Tab-driven escapes to Next/Previous|WrapAround else refocuses origin; InitialFocus ladder initialFocus → AutoFocus scan → first focusable → fallback container → console.warn, all inside one microTask; RestoreFocus replays the global click-history snapshot for the last still-connected element.
- **Layering** — `top-layer-stack-machine`: DefaultMap of per-scope stacks; Push of an existing id MOVES it to top; pop of absent id is a no-op (no refcount); useIsTopLayer returns true when enabled-but-not-yet-on-stack. `inert-others-refcount`: crawl allowed elements' parents marking non-ancestor siblings inert, counts map gates restoration so original attribute values survive overlapping dialogs.
- **Outside interaction** — `outside-click-pointer-pair`: pointerdown stores composedPath[0], pointerup judges that captured target (capture phase beats stopPropagation); touch path uses live target + ≥30px move cancel; window blur treats focused iframe as outside; defaultPrevented events are respected for nested dismissal; clicks on Loose-focusable elements are NOT prevented.
- **Scroll lock** — `scroll-lock-store`: module-level store keyed by Document; PUSH increments count and adds meta fn, subscriber dispatches SCROLL_PREVENT/SCROLL_ALLOW only on hidden-state edges, TEARDOWN at count 0; meta() is lazy so later PUSH/POP refresh computedMeta. `ios-touch-scroll-lock`: force scrollBehavior:auto around body offset, capture anchor-hash clicks, root-container overscroll contain vs touch-action none, touchmove preventDefault only when crawl from target reaches the `[data-headlessui-portal]` boundary without finding an overflowing scroller.
- **Dialog orchestration** — `dialog-wiring-order`: ForcePortalRoot→Portal→Context→PortalGroup→ForcePortalRoot(false)→DescriptionProvider→PortalWrapper→FocusTrap→CloseProvider→render; inertOthers/scrollLock disabled when `isClosing`; Escape blurs activeElement before close. `open-closed-context`: State.Open/Closed/Opening/Closing bits flow down through context; children inherit open state when prop omitted; ResetOpenClosedProvider stops leakage at Dialog boundaries.
- **State plumbing** — `machine-react-glue`: send() reduces, skips subscribers whose shallowEqual slice didn't change, then fires per-event-type listeners; useSlice bridges to React with stable useEvent wrappers. `listbox-dom-order-registry`: RegisterOptions marks pendingShouldSort, rAF-later SortOptions re-sorts by compareDocumentPosition and re-locates the active option by identity (-1→null); GoToOption fast paths skip sorting for Nothing/Specific/adjacent-sibling moves.
- **Listbox behaviors** — `listbox-typeahead`: searchQuery accumulates lowercase, candidate list rotated to start after active (+1 only when starting fresh), first non-disabled prefix match wins, match==active keeps query but doesn't move. `calculate-active-index`: six Focus actions, all-disabled lists return currentActiveIndex unchanged, Previous from nothing starts at length.
- **Forms & portals** — `form-fields-hoisting`: composeKey bracket paths, booleans as 1/0, Date ISO, null→''; attemptSubmit clicks a real submit element (so preventDefault works) falling back to requestSubmit; FormFieldsProvider renders a Hidden marker inside the real <form> and HoistFormFields portals data-driven hidden inputs there. `portal-nesting-registration`: portals reuse `#headlessui-portal-root`, each Portal wraps content in `[data-headlessui-portal]`, useNestedPortals registers children upward recursively; empty group targets self-remove on unmount. `stable-collection-index`: get() bumps a per-key render count and returns insertion index, release runs in effect cleanup — indexes stay stable across SSR hydration reorderings.
- **Outside resolution** — `root-containers-resolution`: default+portal containers first, then every body-level child except head/body/our-portal-root/main-tree ancestor and already-covered subtrees; MainTreeProvider probes with a temporary Hidden to find the main node when the component itself is portalled.
- **Anchoring** — `floating-anchor-config`: gap/offset/padding resolve through a probe element letting the browser compute var()/rem/calc chains, with an rAF poll that only recomputes when raw computed properties change (documented inherited-cascade bug).
- **Primitives** — `hidden-element-styles`: Focusable keeps tab order with aria-hidden=true, Hidden adds display:none only without Focusable. `server-handoff-gating`: server → hydrating → complete three-phase gate via useSyncExternalStore server-snapshot trick. `text-value-computation`: aria-label → aria-labelledby (recursive, comma-join) → clone-strip innerText minus emoji. `focus-visible-tracking`: non-modifier keydown sets data-headlessui-focus-visible, detail===1 click clears, detail===0 click re-sets. `disposables-scheduler`: double-rAF nextFrame, previous-value style restore, flag-cancelled microtasks, one dispose bag per effect. `scrollbar-compensation`: innerWidth−clientWidth before vs clientWidth−offsetWidth after, pad documentElement by the difference. `active-element-history`: 10-entry connected-filtered focusable ring snapshotted at trap-enable for restore replay.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Headless UI monorepo (MIT), `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory project `ext-ui-headlessui` (3,738 nodes / 14,650 edges, FULL mode, generation 2026-08-23T11:11Z, head==base zero drift; parse_partial ×44 confined to line-2 wrapper files, playgrounds CSS, and one portal.test line — none affect cited internals).

## Full view (memory graph)
Revalidate `ext-ui-headlessui` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: BM25 resolves bare Variable names like `overflows`/`stackMachines` poorly — search an adjacent symbol (`useDocumentOverflowLockedEffect`, `PUSH`, `DefaultMap`) instead; react/vue twin packages duplicate every util, cite the `@headlessui-react` path unless the Vue binding is the question.

## Boundaries
Adopt the pure contracts (focus algebra, stack machine, refcounted inert, overflow counter store, calculateActiveIndex, typeahead rotation, form-entry encoding); adapt host-specific wiring (React context providers, useIsoMorphicEffect timing, floating-ui anchoring) to your framework's equivalents; omit the Vue package bodies beyond contract parity, playground apps, and Tailwind preset styling — they consume the captured contracts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`active-element-history.md`](./active-element-history.md)
- [`calculate-active-index.md`](./calculate-active-index.md)
- [`dialog-wiring-order.md`](./dialog-wiring-order.md)
- [`disposables-scheduler.md`](./disposables-scheduler.md)
- [`floating-anchor-config.md`](./floating-anchor-config.md)
- [`focus-in-bitmask-loop.md`](./focus-in-bitmask-loop.md)
- [`focus-trap-guards.md`](./focus-trap-guards.md)
- [`focus-visible-tracking.md`](./focus-visible-tracking.md)
- [`focusable-enumeration.md`](./focusable-enumeration.md)
- [`form-fields-hoisting.md`](./form-fields-hoisting.md)
- [`hidden-element-styles.md`](./hidden-element-styles.md)
- [`inert-others-refcount.md`](./inert-others-refcount.md)
- [`ios-touch-scroll-lock.md`](./ios-touch-scroll-lock.md)
- [`listbox-dom-order-registry.md`](./listbox-dom-order-registry.md)
- [`listbox-typeahead.md`](./listbox-typeahead.md)
- [`machine-react-glue.md`](./machine-react-glue.md)
- [`open-closed-context.md`](./open-closed-context.md)
- [`outside-click-pointer-pair.md`](./outside-click-pointer-pair.md)
- [`portal-nesting-registration.md`](./portal-nesting-registration.md)
- [`root-containers-resolution.md`](./root-containers-resolution.md)
- [`scroll-lock-store.md`](./scroll-lock-store.md)
- [`scrollbar-compensation.md`](./scrollbar-compensation.md)
- [`server-handoff-gating.md`](./server-handoff-gating.md)
- [`stable-collection-index.md`](./stable-collection-index.md)
- [`text-value-computation.md`](./text-value-computation.md)
- [`top-layer-stack-machine.md`](./top-layer-stack-machine.md)
