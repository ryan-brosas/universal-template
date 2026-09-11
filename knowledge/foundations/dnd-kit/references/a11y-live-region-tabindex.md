<!-- capsule-v2 -->
# Accessibility plugin — batched attribute mutation + debounced live-region announcements

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which attributes must be synthesized on draggable activators, and why are DOM writes funneled through a scheduler with change-guards?

## Accessibility (a11y) plugin
**Path/Symbol:** `packages/dom/src/core/plugins/accessibility/Accessibility.ts:50-231` (+ LiveRegion.ts, HiddenText.ts, defaults.ts).
**Signature:** constructor options `{id?, idPrefix?, announcements?, screenReaderInstructions?, debounce? = 500}`; announcement events map over monitor event names; debounced set = only `['dragover','dragmove']`.
**Data Shape:** hidden instruction div (`display:none`, aria-describedby target) + visually-hidden live region (`role=status aria-live=polite aria-atomic=true` clipped to 1px); both re-created if removed from the DOM (`!el.isConnected` check inside the effect).

### Decisive source
```ts
const mutations = new Set<() => void>();
this.registerEffect(() => {
  mutations.clear();
  for (const draggable of this.manager.registry.draggables.value) {
    const activator = draggable.handle ?? draggable.element;
    if (!activator) continue;
    ...
    if ((!isFocusable(activator) || isSafari()) && !activator.hasAttribute('tabindex'))
      mutations.add(() => activator.setAttribute('tabindex', '0'));
    if (!activator.hasAttribute('role') && activator.tagName.toLowerCase() !== 'button')
      mutations.add(() => activator.setAttribute('role', defaultAttributes.role));
    ... aria-roledescription / aria-describedby / aria-pressed|grabbed (isDragging)
        / aria-disabled (disabled) — each guarded by getAttribute !== desired
  }
  if (mutations.size > 0) scheduler.schedule(executeMutations);
});

// announcement listener
if (announcement && element.nodeValue !== announcement) {
  latestAnnouncement = announcement;
  if (debouncedEvents.includes(eventName)) debouncedUpdateAnnouncement();
  else { scheduleUpdateAnnouncement(); debouncedUpdateAnnouncement.cancel(); }
}
```

**Flow:** effect tracks the draggables registry → for each activator compute the NEEDED attribute writes but only enqueue the ones whose current value differs → flush all via ONE scheduled task (rAF when available). Announcements: monitor listeners build strings per event; non-debounced events (dragstart/end/cancel) schedule immediately AND cancel any pending debounced write so terminal messages are never swallowed by the 500ms window.
**Invariant:** every attribute write is idempotent and guarded (never clobber author-set roles/tabindex); Safari forces tabindex because it skips non-focusable elements for VO; text node updates compare `nodeValue` first — screen readers announce on DOM change, so no-op writes would spam; teardown removes injected nodes and unsubscribes listeners.
**Probe:** no upstream unit file targets this plugin directly (DOM/a11y coverage caveat); behavior pinned indirectly by keyboard-sensor suite (focus flows through these attributes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Accessibility", name_pattern: "^Accessibility$", limit: 10 });
```

## Verdict
Adopt the needed-diff-then-single-flush mutation pattern and the debounced/immediate announcement split; adapt default announcement copy to your locale; omit the Safari tabindex carve-out at the cost of VoiceOnly users being unable to start drags.
