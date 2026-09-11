<!-- capsule-v2 -->
# Feedback rendering — placeholder cloning, popover promotion, and the transform-capture race

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does the dragged element get visually promoted (clone/move/overlay) while keeping layout stable, and which reads must happen BEFORE the dragging attribute flips?

## Feedback plugin
**Path/Symbol:** `packages/dom/src/core/plugins/feedback/Feedback.ts:70-612` + `utilities.ts` (createPlaceholder/proxyDroppableElements) + `dropAnimation.ts`.
**Signature:** options `{feedback?: 'default'|'move'|'clone'|'none', rootElement?, dropAnimation?: DropAnimation|null, keyboardTransition?}`; per-entity override via `source.pluginConfig(Feedback)`; render effect `#render` re-runs on drag state.
**Data Shape:** `state.initial` captures {dimensions, coordinates, frameTransform, translate, transformOrigin} once; `state.current.translate` accumulates applied transforms.

### Decisive source
```ts
// Feedback.ts :191-203 — the capture-before-attribute race
// Filter out transform-related transitions that would interfere with
// Feedback-managed properties (--dnd-transform, --dnd-translate, --dnd-scale)
const feedbackTransition = transition.split(',')
  .filter((t) => !/^\s*(transform|translate|scale)\b/.test(t)).join(',');
const parsedTransform = parseTransform(elementStyles);
// Eagerly capture the raw transform CSS value before the
// data-dnd-dragging attribute is set, since elementStyles is a live
// CSSStyleDeclaration and the CSS rule for [data-dnd-dragging] overrides
// transform via !important, which would cause the live object to return
// the overridden value instead of the original.
const initialTransformStyle = elementStyles.transform;

// utilities.ts — placeholder keeps nested droppables ALIVE via proxying
droppable.proxy = clonedElement;
ProxiedElements.set(originalElement, clonedElement);
cleanup.push(() => { ProxiedElements.delete(originalElement); droppable.proxy = undefined; });

// dropAnimation.ts :146-155 — animation only when it actually moved
duration: prefersReducedMotion(...) ? 0
  : ctx.moved || ctx.feedbackElement !== ctx.element ? duration : 0,
```

**Flow:** on first initialized render: measure geometry (cross-frame scale deltas via `getFrameTransform`), compute `transformOrigin` from cursor position over the VISUAL rect, set width/height/top/left + `translate` custom-property styles, insert a placeholder (`cloneElement` with `inert`, `aria-hidden`, proxied nested droppables so hit-testing still resolves through the clone), optionally reparent the source into an overlay root, promote to `popover=manual` when supported (escapes every clipping ancestor) with a `beforetoggle` guard preventing user-agent closes. On each move effect: write translate + advance `dragOperation.shape` by the delta. On dropped: run the drop animation toward the placeholder slot (min/max-size keyframes when dimensions differ), then cleanup restores saved table-cell widths, resets status to idle, and re-focuses for keyboard drags.
**Invariant:** transform/translate/scale transitions are stripped from the feedback element's transition list (they fight the 0ms-linear translate writes); the ORIGINAL computed transform must be read before `[data-dnd-dragging]` applies its !important override (live CSSStyleDeclaration hazard); window resize during a KEYBOARD drag stops the operation (coordinates become meaningless).
**Probe:** no direct unit suite for Feedback (DOM-heavy coverage caveat); ordering contract referenced by `drag-event-order.test.ts:53-62` which mimics "shape set when initialized && !initializing".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Feedback", name_pattern: "^Feedback$", limit: 10 });
```

## Verdict
Adopt capture-before-attribute-apply ordering, placeholder proxying of nested droppables, and moved-gated drop animations; adapt popover promotion to your stacking-context strategy; omit table-cell-width preservation unless you support dragging `<tr>`.
