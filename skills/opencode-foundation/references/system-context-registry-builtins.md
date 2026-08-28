<!-- capsule-v2 -->
# System-context registry + builtins — how do you let plugins and sessions contribute system context that appears and disappears with their lifetime, in a deterministic order?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Multiple components (built-ins, instruction discovery, future plugins) need to contribute system context whose lifetime is scoped to their own. How do you register scoped contributors, keep ordering deterministic, and fail loudly on identity collisions — without letting one contributor's death corrupt the registry?

## Scope-lifetime registry
**Path/Symbol:** `packages/core/src/system-context/registry.ts` (`Entry` :9, `register` :25-38, `load` :39-46, `Service` :18).
**Signature:** `register(entry: Entry) → Effect<void, never, Scope.Scope>`; `load() → Effect<SystemContext>`.
**Data Shape:** `Entry = { key: SystemContext.Key, load: Effect<SystemContext> }` — an entry's load produces a WHOLE composed context (possibly multi-source), not a single source.

### Decisive source
```ts
// registry.ts:25-38 — acquireRelease registration; duplicate entry key dies
yield* Effect.acquireRelease(
  Ref.modify(entries, (current) => {
    if (current.some((item) => item.key === entry.key)) return [false, current]
    return [true, [...current, entry]]
  }).pipe(
    Effect.flatMap((added) => added ? Effect.void : Effect.die(`Duplicate system context entry key: ${entry.key}`)),
    Effect.as(entry),
  ),
  (entry) => Ref.update(entries, (current) => current.filter((item) => item !== entry)),
)
```

**Flow:** register adds the entry inside acquireRelease, so closing the owning Scope removes exactly that entry (contributor death cleans up its context). load() re-evaluates every entry's producer on EACH call (no caching — dynamic contributors re-derive their context), sorts entries by key, and hands the composed contexts to SystemContext.combine, which re-checks duplicate SOURCE keys. Two distinct failure points: duplicate ENTRY key dies at register time; duplicate SOURCE key (two entries exposing the same source key) dies at load/combine time.
**Invariant:** registration lifetime = caller scope; per-load re-evaluation means registry state is never stale; key-sorted combine gives deterministic baseline order regardless of registration order; identity collisions are defects, not silent overrides.
**Probe:** `packages/core/test/system-context/registry.test.ts` (7 `it.effect` cases): "removes an entry when its owning scope closes" pins scope-lifetime removal; "loads scoped entries in stable key order" pins sorted output ("first\n\nsecond" from reverse-order registration); "re-evaluates entry producers on each load" pins loads=2 after two load() calls; "rejects duplicate entry keys" pins the register-time die; "rejects duplicate source keys from separate entries" pins the combine-time DuplicateKeyError. Source pin:
```bash
grep -c 'Duplicate system context entry key' packages/core/src/system-context/registry.ts   # expect 1
grep -c 'toSorted' packages/core/src/system-context/registry.ts   # expect 1
grep -c 'acquireRelease' packages/core/src/system-context/registry.ts   # expect 1
```

## Builtins: environment + date sources
**Path/Symbol:** `packages/core/src/system-context/builtins.ts` (`environment` :25-32, `core/date` :34-40, registration :42-44).
**Signature:** one composite registry entry `core/builtins` whose load returns `SystemContext.combine([environment, date])`.
**Data Shape:** environment renders `<env>` block (working directory, workspace root, git-repo flag, platform); date source value = `date.toDateString()`.

### Decisive source
```ts
// builtins.ts:34-40 — calendar-day granularity via toDateString
SystemContext.make({
  key: SystemContext.Key.make("core/date"),
  codec: Schema.toCodecJson(Schema.String),
  load: DateTime.nowAsDate.pipe(Effect.map((date) => date.toDateString())),
  baseline: (date) => `Today's date: ${date}`,
  update: (_previous, date) => `Today's date is now: ${date}`,
})
```

**Flow:** builtins register once at layer build; the date source's codec value is the toDateString string, so a refresh within the same local calendar day compares equal (Unchanged) and only a day boundary produces an Updated "Today's date is now:" — the compare ladder does the granularity work, not the producer. Instruction-context composes after builtins in the baseline (pinned by test).
**Invariant:** date granularity is a property of the source VALUE (calendar-day string), not of a timer; unchanged sources never re-render.
**Probe:** `packages/core/test/system-context/builtins.test.ts` (3 `it.effect` + 1 `itWithInstructions.effect`, TestClock-pinned): "does not update again within the same local calendar day" pins Unchanged after +1h; "reconciles the date without repeating unchanged environment context" pins the day-boundary update text; "composes ambient instructions after built-in context" pins instruction-context's position after builtins. Source pin:
```bash
grep -c 'core/date' packages/core/src/system-context/builtins.ts   # expect 1
grep -c 'toDateString' packages/core/src/system-context/builtins.ts   # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SystemContextRegistry register acquireRelease scope entry load combine builtins environment date", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the scope-lifetime registry with acquireRelease cleanup and the two-level duplicate check (entry key at register, source key at combine); adopt per-load producer re-evaluation for dynamic contributors; adopt value-encoded granularity (toDateString) so the compare ladder handles refresh cadence. Adapt the Layer/node wiring to your DI framework; omit the builtins content itself (it is opencode-specific). Direct tests read whole (registry.test.ts 114L, builtins.test.ts 129L); bun runner blocked at this checkout, probes are byte-exact greps.
