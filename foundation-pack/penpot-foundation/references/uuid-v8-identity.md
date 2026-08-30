<!-- capsule-v2 -->
# UUIDv8 identity — time-sortable IDs with deterministic fakes for tests

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** How does penpot generate identity across JVM and JS such that IDs sort by creation time AND tests can pin exact ids?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/uuid.cljc` : whole file — `next`/`random`/`custom` (:51-65), `zero` (:67), bytes roundtrip (:83-100), fake generator (:141-155).
**Signature:** `(uuid/next) → UUID` · `(uuid/custom high low) → UUID` · `(uuid/next-fake) → sequential UUID` · `(uuid/coerce v) → uuid|nil`.
**Data Shape:** CLJ delegates to custom `app.common.UUIDv8/create` (Java class at common/src); CLJS to `app.common.uuid-impl/v8`. All APIs return native platform UUID objects (`java.util.UUID` / js `UUID`).

### Decisive source
```clojure
(defn next []
  #?(:clj  (UUIDv8/create)
     :cljs (uuid (impl/v8))))

(def ^:private fake-ids (atom 0))
(defn reset-fake! "Reset the fake uuid counter to 0, for reproducible results across tests." []
  (reset! fake-ids 0))
(defn next-fake "When you need predictable uuids, … wrap the code with
     (with-redefs [uuid/next uuid/next-fake] …)" []
  (-> (swap! fake-ids inc) (custom)))
```

**Flow:** `next()` = v8 time-ordered id (monotonic within process, sorts lexicographically by time) used for ALL new shapes/pages/files so DB indexes stay append-friendly → `custom(high low)` builds an exact UUID from raw longs — the basis of both `zero` and the fake sequence (1,2,3…) → tests inject determinism via `with-redefs`, never by threading an RNG through production code → `parse*` returns nil on invalid strings while strict `parse` throws with the offending value embedded.
**Invariant:** identity type stays the PLATFORM native UUID on both runtimes — records/maps never carry string ids internally; `uuid?` checks are instance checks. The zero UUID doubles as the synthetic page-id for component/container scopes (see changes-builder capsule).
**Probe:** `grep -cF '#?(:clj (UUIDv8/create)' common/src/app/common/uuid.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "next-fake reset-fake custom parse coerce", limit: 10, fields: ["signature","name","file"] });
```
(verified live: `…uuid.next-fake Function common/src/app/common/uuid.cljc 149-155`)

## Verdict
Adopt time-ordered v8 + native-type discipline for any multi-runtime document store; adapt the Java impl if not on JVM (any UUIDv7 lib preserves the sortability invariant); omit wasm u32-part accessors. Tests: types/token_test and others rely on `next-fake` determinism (runner blocked honestly).
