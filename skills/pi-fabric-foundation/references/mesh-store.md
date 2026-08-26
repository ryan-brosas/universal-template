<!-- capsule-v2 -->
# Mesh store — append-only event log + key-version CAS state

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does a multi-process mesh share events and state with bounded growth and cross-process safety?

## Connected graph-selected seam
**Path/Symbol:** `src/mesh/store.ts` (852 lines): `MeshStore` (:197), `publish` (:248+), `#eventsPath`/`#statePath`/`#counterPath`/`#generationPath`/`#lockPath` (:219-223).
**Signature:** `publish({topic, kind?, from, to?, text?, data?})` — validates the topic, appends to `events.jsonl`; state is a `state.json` with key-version CAS puts; a `.lock` file with timeout/stale detection coordinates cross-process writes.
**Data Shape:** event log bounded by `maxEventLogBytes` (capped at `CURSOR_OFFSET_BASE - 1`), retained tail `retainedEventLogBytes`; state bounded by `maxStateBytes` + `maxStateTombstones`; lock `lockTimeoutMs`/`staleLockMs`.

### Decisive source
```ts
this.#eventsPath = path.join(root, "events.jsonl")
this.#statePath = path.join(root, "state.json")
this.#counterPath = path.join(root, "sequence")
this.#generationPath = path.join(root, "generation")
this.#lockPath = path.join(root, ".lock")
// event log capped at CURSOR_OFFSET_BASE-1; retained tail bounded
// state.json with key-version CAS; .lock with timeout + stale detection
```

**Flow:** processes publish events (append-only JSONL, bounded + retained-tail); state lives in `state.json` updated via key-version CAS puts (optimistic concurrency); a `.lock` file with timeout + stale-lock detection coordinates cross-process mutations; a sequence counter + generation file track ordering.
**Invariant:** event log and state are bounded (never grow unbounded); CAS puts prevent lost updates; stale locks are recoverable.
**Probe:** `tests/` mesh coverage (publish appends + validates topic; CAS put rejects a stale version; lock timeout/stale recovery; event-log truncation to retained tail).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "MeshStore publish state CAS lock events jsonl bounded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the append-only event log + key-version CAS state + lock-file coordination with bounded growth; adapt the paths and byte budgets to host.
