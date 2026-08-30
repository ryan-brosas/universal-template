<!-- capsule-v2 -->
# Project store indirection — handlers hold `value | null | () => value` refs so project binding can be resolved lazily and rebind without re-registration

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Seven handlers need the active project's store/name, but the project is detected at runtime (and can change or be absent) — how do you wire them without freezing stale bindings at registration time?

## resolveProjectStore / resolveProjectName
**Path/Symbol:** `src/project-context.ts` (whole file, 13 L): `ProjectStoreRef = MemoryStore | null | (() => MemoryStore | null)`, `ProjectNameRef = string | null | (() => string | null | undefined)`; `resolveProjectStore(ref)` unwraps functions; `resolveProjectName(ref)` unwraps THEN trims with `value?.trim() || null`.
**Signature:** `resolveProjectStore(ref: ProjectStoreRef) → MemoryStore | null`; `resolveProjectName(ref: ProjectNameRef) → string | null`.
**Data Shape:** consumers (`background-review.ts`, `correction-detector.ts`, `session-flush.ts`, `insights.ts`, `auto-consolidate.ts`, `preview-context.ts`, `tools/memory-tool.ts`) all accept the ref form at setup time.

### Decisive source
```ts
export function resolveProjectStore(ref: ProjectStoreRef): MemoryStore | null {
  return typeof ref === "function" ? ref() : ref;
}
export function resolveProjectName(ref: ProjectNameRef): string | null {
  const value = typeof ref === "function" ? ref() : ref;
  return value?.trim() || null;   // "" / whitespace collapse to NULL — "no project"
}
```

**Flow:** extension setup passes a closure (typically `() => projectManager.getActiveStore()`); every handler calls the resolver AT EVENT TIME, so a worktree switch or late project detection is picked up on the next event without touching registrations. Static values remain legal for embedders that know their project up front.
**Invariant:** empty-string project names must normalize to null BEFORE any scope decision — a porter who trusts a trimmed-later name creates an invisible `[ ]` global/project scope mismatch (memory rows keyed under `""`). The tri-state ref exists because null ("no project") and not-yet-resolved are DIFFERENT states that both arrive as null only after calling.
**Probe:** no dedicated upstream suite isolates this helper (it is exercised transitively through every handler suite listed in Data Shape — e.g. `tests/handlers/session-flush.test.ts`, `tests/handlers/background-review.test.ts`). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "resolveProjectStore resolveProjectName ProjectStoreRef", limit: 5 })`

## Verdict
Adopt for any multi-consumer wiring over state that resolves late. Adapt types; keep lazy-call-time resolution and trim-to-null name normalization. Omit nothing — 13 lines whose value is the registration-time-vs-event-time distinction.
