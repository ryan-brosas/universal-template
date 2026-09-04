<!-- capsule-v2 -->
# Disposables scheduler — how do rAF pairs, microtasks, and style writes get cancelled as one unit?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the disposables API surface (nextFrame, style, group, add-dedupe) that every DOM-touching hook in the library builds on?

## disposables / nextFrame / style / group / add
**Path/Symbol:** `packages/@headlessui-react/src/utils/disposables.ts:17-97`; microTask fallback `utils/micro-task.ts:2-14`.
**Signature:** `disposables(): { addEventListener(el, name, listener, options?): () => void; requestAnimationFrame(...): () => void; nextFrame(cb): void; setTimeout(...): () => void; microTask(cb): () => void; style(node, prop, value): () => void; group(cb): () => void; add(cb): () => void; dispose(): void }`.
**Data Shape:** `add` returns an "invoke-and-remove" closure; duplicate callbacks are registered ONCE (`includes` check); dispose splices-as-it-iterates so cleanups can add new disposables safely.

### Decisive source
```ts
nextFrame(...args) {                    // TWO frames: styles committed, transitions startable
  return api.requestAnimationFrame(() => api.requestAnimationFrame(...args))
}
style(node, property, value) {
  let previous = node.style.getPropertyValue(property)
  Object.assign(node.style, { [property]: value })
  return this.add(() => Object.assign(node.style, { [property]: previous }))   // restore EXACT previous
}
group(cb) { let d = disposables(); cb(d); return this.add(() => d.dispose()) }
microTask(...args) {                    // cancellation flag because queueMicrotask can't be cancelled
  let task = { current: true }
  microTask(() => { if (task.current) args[0]() })
  return api.add(() => { task.current = false })
}
// polyfill ladder in micro-task.ts:
if (typeof queueMicrotask === 'function') queueMicrotask(cb)
else Promise.resolve().then(cb).catch((e) => setTimeout(() => { throw e }))
```

**Flow:** every scheduling primitive registers its own canceler → `dispose()` runs and EMPTIES the list (splice(0)) so re-dispose is safe and late additions during cleanup still get cleaned → `restoreFocusIfNecessary`, iOS scroll-lock, scrollbar-padding all compose through one bag per lock/step.
**Invariant:** nextFrame is deliberately DOUBLE-rAF — single rAF can fire before style flush; style() snapshots the PREVIOUS inline value rather than deleting the property; microTask "cancellation" is a flag check (the callback DOES run, it no-ops).
**Probe:** deterministic checks executed: dedupe-by-reference, splice-empty safety, flag-cancel semantics. Direct coverage: transitive via every effect-driven suite (dialog open/close timing asserts rely on nextFrame ordering).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "disposables nextFrame", name_pattern: "^disposables$", limit: 5 });
```

## Verdict
Adopt the whole utility verbatim as your DOM-effect bag; adapt only the microTask polyfill branch to your browser floor. The double-rAF and style-restore semantics are load-bearing across focus restore AND scroll locking — don't flatten them to single-rAF.
