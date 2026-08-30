<!-- capsule-v2 -->
# File-data backend switch — how do you flip a storage backend default (legacy-db → db) without breaking rows written under the old default?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (config.clj `:file-data-backend "legacy-db"` → `"db"`); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What does the dispatch key actually control, and what must stay in place for old rows?

## resolve-file-data trimodal read + write dispatch
**Path/Symbol:** `backend/src/app/features/fdata.clj` (`resolve-file-data` multimethod :85-106, `handle-persistence` :149-207, `default-backend` :215-217) + `backend/src/app/config.clj` :52-55.
**Signature:** `(resolve-file-data cfg file) -> file'`; `(handle-persistence cfg params) -> row`.
**Data Shape:** file-data row: `{... :backend ("db"|"storage"|"legacy-db") :type ("main"|"snapshot"|"fragment") :data bytes|nil :metadata …}`. Dispatch reads `(get file :backend "legacy-db")` — the ROW's stored backend, not config.

### Decisive source
```clojure
(defmulti resolve-file-data
  (fn [_cfg file] (get file :backend "legacy-db")))

(defmethod resolve-file-data "storage"
  [cfg {:keys [metadata] :as file}]
  (let [ref-id (:storage-ref-id metadata)
        data   (->> (sto/get-object storage ref-id)
                    (sto/get-object-bytes storage))]
    (-> file (assoc :data data) (dissoc :legacy-data))))
```

**Flow:** WRITES take the backend from config (`(cf/get :file-data-backend)` via `default-backend`, now defaulting `"db"`); READS dispatch on the per-row `:backend` value with legacy fallback. The three write branches differ materially: storage = blob to object store + pointer in metadata + data nil; db = bytes inline, metadata kept minus pointer; legacy-db main/snapshot = DELETE row then UPDATE the OLD tables (`file` / `file-change`) — fragment still upserts as plain db row.
**Invariant:** Old-format rows remain readable because the dispatch key lives on the row and every branch normalizes to the same post-shape (`:data` present, `:legacy-data` absent). Flipping the DEFAULT changes only where NEW writes land; it is not a migration of existing rows.
**Probe:** deterministic greps from repo root: `grep -n '"legacy-db"' backend/src/app/features/fdata.clj | wc -l` → 4 (dispatch fallback :86, two resolve/write arms, fragment re-tag); `grep -n ':file-data-backend' backend/src/app/config.clj` → :55 default `"db"` and :263 schema enum `[:enum "db" "legacy-db" "storage"]`.
**Coverage caveat:** behavior change covered by repo test suite only indirectly (binfile roundtrip uses the configured backend); no unit test pins the default flip itself.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"resolve-file-data","limit":4,"detail":"ids"}'
```

## Verdict
Adopt row-keyed read dispatch + config-keyed write dispatch as the safe backend-flip shape. Adapt backends/tables to your stack. Omit Penpot's legacy table names if you have no legacy window.
