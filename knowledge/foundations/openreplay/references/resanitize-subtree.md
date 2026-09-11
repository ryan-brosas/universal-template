<!-- capsule-v2 -->
# resanitize two-way re-emit — how do you change masking AFTER recording started without corrupting the player DOM?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** When a `data-openreplay-*` attribute or domSanitizer predicate flips at runtime, what is the safe re-record choreography?

## Hidden-boundary crossing rebuilds; level flips re-emit
**Path/Symbol:** `tracker/tracker/src/main/app/observer/observer.ts` — `resanitizeSubtree` (:729–738), `resanitizeNode` (:740–771), `recreateSubtree` (:775–784), `clearSubtreeRegistration` (:786–813), `reemitNode` (:815–828); public entry `API.resanitize(el?)` in `main/index.ts:325–330`.
**Signature:** `resanitizeSubtree(root: Node): void`; `recreateSubtree(node: Node): void`; callback registration via `app.attachResanitizeCallback((node, id) => …)`.
**Data Shape:** Walk state = `(node, parentLevel)`. Three outcomes per node: structure rebuild (hidden boundary), leaf re-emit (Plain↔Obscured), or no-op.

### Decisive source
```ts
// Crossing the hidden boundary changes the rendered structure (placeholder vs
// real subtree), so rebuild rather than re-emit.
if (wasHidden !== willHidden) { this.recreateSubtree(node); return }
if (willHidden) { return }
// Plain <-> Obscured: same structure, only leaf content changes.
if (prevLevel !== newLevel) {
  this.app.sanitizer.setLevel(id, newLevel)
  this.reemitNode(id, node)
}
for (let child = node.firstChild; child !== null; child = child.nextSibling)
  this.resanitizeNode(child, newLevel)
```

**Flow:** compute new level from live DOM → if hidden-ness changed: `RemoveNode(id)` → unregister whole subtree (collect-first-then-clear so the walker isn't mutated mid-iteration; reset each node's sanitizer level to Plain) → re-bind + commit with fresh ids. Otherwise just `setLevel` + re-send text/attribute payloads through registered resanitize callbacks (input module re-sends `SetInputValue`; img re-evaluates placeholder).
**Invariant:** Untracked nodes are skipped (`getID === undefined`) — the live observer owns them; a porter must NOT create ids during resanitize. Placeholder-vs-real swaps only happen on hidden-boundary crossings, never on Plain↔Obscured.
**Probe:** `grep -c 'wasHidden !== willHidden' tracker/tracker/src/main/app/observer/observer.ts` → `1`; `grep -c 'Collect first, then clear' tracker/tracker/src/main/app/observer/observer.ts` → `1`; direct test coverage via sanitizer two-way suite (`tests/sanitizer.unit.test.ts` describe `two-way level state`, executed green).
**Coverage:** observer.ts clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "resanitizeSubtree recreateSubtree reemitNode", limit: 10 });
```

## Verdict
Adopt boundary-crossing-rebuilds semantics — it's what keeps player-side DOM consistent after runtime privacy toggles. Adapt the callback registry to your event bus. Omit iframe/cross-domain resanitize variants unless you port the frame proxy too.
