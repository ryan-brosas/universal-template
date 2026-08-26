<!-- capsule-v2 -->
# Dep/Link twin intrusive lists — how are many-to-many dep↔subscriber edges stored, re-used, and torn down without leaks?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** How does a porter wire the dependency graph so an effect re-subscribes to only the deps it actually read last run, and unsubscribes exactly once?

## Link nodes shared by two doubly-linked lists
**Path/Symbol:** `packages/reactivity/src/dep.ts:Link` (:32-62), `Dep` (:67-106), `Dep.track` (:108-165), `addSub` (:207-232); `packages/reactivity/src/effect.ts:removeSub` (:432-470), `removeDep` (:472-482).
**Signature:** `class Link { sub: Subscriber; dep: Dep; version: number; nextDep/prevDep/nextSub/prevSub/prevActiveLink?: Link }`, `track(debugInfo?): Link | undefined`.
**Data Shape:** One `Link` instance per live (sub, dep) pair; it is simultaneously a node in the sub's dep list (`deps…depsTail`, via prev/nextDep) and the dep's subscriber list (`subs` tail pointer, via prev/nextSub). `Dep.sc` counts subscribers; `Dep.activeLink` memoizes the current sub's link; `link.version` mirrors `dep.version` at last tracked read.

### Decisive source
```ts
// Dep.track: reuse the existing link when the same sub reads the same dep again
let link = this.activeLink
if (link === undefined || link.sub !== activeSub) {
  link = this.activeLink = new Link(activeSub, this)
  if (!activeSub.deps) { activeSub.deps = activeSub.depsTail = link } else { /* append at tail */ }
  addSub(link)
} else if (link.version === -1) {
  // reused from last run - already a sub, just sync version
  link.version = this.version
  if (link.nextDep) { /* unlink from mid-list and move to tail */ }
}
```

**Flow:** run start → `prepareDeps` stamps every existing link `version = -1` (effect.ts :312-322) → during `fn()` each `dep.track()` either creates a Link+`addSub` or resurrects the stale link by syncing version and moving it to the tail → run end → `cleanupDeps` (effect.ts :324-351) walks the list backward and removes every still `-1` link from BOTH lists (`removeSub` + `removeDep`), restoring `dep.activeLink` from `prevActiveLink` on the way.
**Invariant:** A dep↔sub pair is represented by AT MOST one Link; subscription count (`dep.sc`) is incremented only in `addSub` and decremented only in non-soft `removeSub` — porters who rebuild lists as arrays/Sets per run lose O(1) reuse and break `sc` accounting that property-dep GC depends on (`if (!soft && !--dep.sc && dep.map) dep.map.delete(dep.key)`, effect.ts :463-469, the #11979 memory fix).
**Probe:** `packages/reactivity/__tests__/gc.spec.ts:34` (`should release reactive property dep` — after computed drop + gc, `getDepFromReactive(src,'foo')` must be undefined).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "Link addSub removeSub", limit: 10 });
```

## Verdict
Adopt the Link-node/two-lists design and version=-1 sweep verbatim — it is the whole incremental-trickery of the kernel. Adapt storage layout only under measurement (upstream chose raw Map over Set deliberately, comment at dep.ts :234-237). Omit the DEV-only `subsHead` mirror (onTrigger ordering) unless you ship devtools hooks.
