<!-- capsule-v2 -->
# Scroll-lock store — how do N concurrent Dialogs share one body lock without double-applying styles?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the refcount/state protocol that applies and releases scroll prevention exactly once regardless of lock count?

## overflows store + PUSH/POP/SCROLL_PREVENT/SCROLL_ALLOW/TEARDOWN
**Path/Symbol:** `packages/@headlessui-react/src/hooks/document-overflow/overflow-store.ts:36-132`; hook `use-document-overflow.ts:5-27` (`useDocumentOverflowLockedEffect`).
**Signature:** `overflows = createStore(() => new Map<Document, DocEntry>(), { PUSH(doc, meta), POP(doc, meta), SCROLL_PREVENT(entry), SCROLL_ALLOW(entry), TEARDOWN(entry) })`; `DocEntry { doc, count, d: Disposables, meta: Set<MetaFn>, computedMeta }`; `MetaFn = (meta) => Record<string, any>`.
**Data Shape:** keyed by Document (iframe/multi-doc safe); `count` is the refcount; `computedMeta` is re-folded from ALL live meta fns after every push/pop.

### Decisive source
```ts
PUSH(doc, meta) {
  let entry = this.get(doc) ?? { doc, count: 0, d: disposables(), meta: new Set(), computedMeta: {} }
  entry.count++
  entry.meta.add(meta)
  entry.computedMeta = buildMeta(entry.meta)   // Object.assign fold in insertion order
  this.set(doc, entry); return this
}
// subscriber — runs OUTSIDE React:
for (let entry of docs.values()) {
  let isHidden = styles.get(entry.doc) === 'hidden'
  let isLocked = entry.count !== 0
  let willChange = (isLocked && !isHidden) || (!isLocked && isHidden)
  if (willChange) overflows.dispatch(entry.count > 0 ? 'SCROLL_PREVENT' : 'SCROLL_ALLOW', entry)
  if (entry.count === 0) overflows.dispatch('TEARDOWN', entry)
}
// lazy meta view so later pushes keep steps fresh:
meta() { return entry.computedMeta }
```

**Flow:** component effect dispatches PUSH on lock / POP on cleanup → module-level subscriber diffs each document's inline overflow against its lock count → only EDGE transitions run the step pipeline (`handleIOSLocking → adjustScrollbarPadding → preventScroll`, all `before`s then all `after`s into a shared Disposables) → TEARDOWN deletes the entry at zero to avoid leaking Documents.
**Invariant:** a second PUSH while locked does NOT re-run steps (already hidden ⇒ no edge); meta is read LAZILY inside steps via `ctx.meta()` so a later PUSH's containers are visible to still-running locks; actions returning undefined don't notify (store.ts `if (newState)` gate — live-probed). The same MetaFn instance must be passed to PUSH and POP because meta lives in a Set.
**Probe:** live `/tmp/hui-pass1-probe/probe-stack-inert-overflow.mjs`: willChange edges true/false per matrix; buildMeta last-wins-per-key. Direct test: dialog.test.tsx asserts `documentElement.style.overflow === 'hidden'` while open and restoration after close; graph probe resolves PUSH/POP/meta nodes line-exact in overflow-store.ts.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useDocumentOverflowLockedEffect", name_pattern: "^useDocumentOverflowLockedEffect$", limit: 5 });
```

## Verdict
Adopt the counter+edge-detection store verbatim (it's what makes nested dialogs safe); adapt the step list to your platform needs but keep before-all/after-all ordering and shared disposables; omit the Vue twin differences. Caveat: createStore notifies ONLY when the action returns a truthy new state — porters who return void from mutating actions will silently lose reactivity.
