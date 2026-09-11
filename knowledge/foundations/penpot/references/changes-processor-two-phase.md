<!-- capsule-v2 -->
# Changes processor — how do ~40 heterogeneous change types reduce onto one immutable file-data map?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** How does penpot dispatch arbitrary change maps onto nested file data while still tracking cross-cutting effects (component "touched" flags, media-ref fixes)?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/files/changes.cljc` : `process-changes` / `*touched-changes*` / `*state*` / `process-children-reordering` (:455-664).
**Signature:** `(defmulti process-change (fn [_ change] (:type change)))` · `(process-changes data items verify?)`.
**Data Shape:** `data` = file-data map (`:pages-index {page-id {… :objects}}`, `:components {…}`); each change is a schema'd map keyed by `:type` (`:add-obj`, `:mod-obj`, `:del-obj`, `:mov-objects`, `:reorder-children`, `:reg-objects`, `:set-guide`, …).

### Decisive source
```clojure
(def ^:dynamic *touched-changes*
  "A dynamic var that used for track changes that touch shapes on
  first processing phase of changes." nil)
(def ^:dynamic *state* …)

(defn process-changes ([data items] (process-changes data items true))
  ([data items verify?]
   (when verify? (check-changes items))
   (binding [*touched-changes* (volatile! #{})]
     (let [result (reduce #(or (process-change %1 %2) %1) data items)]
       (reduce process-touched-change result @*touched-changes*)))))
```

**Flow:** validate once (`verify?` lets callers skip revalidation when applying twice) → bind a fresh touched-set → fold changes left-to-right through `process-change` multimethods, each returning a NEW immutable data map (a method returning nil is treated as identity via `(or (process-change %1 %2) %1)`) → second pass replays collected "touched" changes to mark component roots modified. Reordering (`process-children-reordering` :636-658) sorts existing children by a sparse `id→idx` map with `d/nilv … -1` fallback so unmentioned ids keep relative order at the front, and refuses to reorder inside component copies unless `allow-altering-copies`.
**Invariant:** every `process-change` method is a pure function `(data change) → data'`; side channels (`*touched-changes*`, `*state*`) are strictly bound-scoped and drained by the second phase — a porter who mutates data in place or forgets phase two breaks component-sync bookkeeping silently.
**Probe:** `grep -cF 'binding [*touched-changes* (volatile! #{})]' common/src/app/common/files/changes.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "process-children-reordering process-change mod-obj add-obj", limit: 10, fields: ["signature","name","file"] });
```
(verified live: resolves `…files.changes.process-children-reordering Function common/src/app/common/files/changes.cljc 636-658`)

## Verdict
Adopt the pure multimethod reducer + bound side-channel second phase as the canonical pattern for event-sourced document edits; adapt the specific change-type zoo to your domain; omit backend-only hard validation (`validate-shape` runs `#?(:clj …)` only). Coverage caveat: `changes.cljc` indexed clean (no_recorded_issue) but is 1244 lines — only the processor core and reorder logic are cited here.
