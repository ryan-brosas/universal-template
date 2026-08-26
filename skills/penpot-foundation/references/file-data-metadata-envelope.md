<!-- capsule-v2 -->
# File-data metadata envelope — how do you carry per-blob provenance through a multi-backend storage layer without leaking storage internals?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (feature landed in 47d599f "Persist binfile manifest and emit workspace audit events"); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How does a file gain a small metadata map (storage pointer + import provenance) that survives db/storage/legacy backends and a schema change?

## schema:file-metadata + backend-split persistence
**Path/Symbol:** `common/src/app/common/types/file.cljc` (`schema:file-metadata` :91-95, `:metadata` on `schema:file` :115, `decode-file-metadata` :133-134) + `backend/src/app/features/fdata.clj` (`handle-persistence` :149-207, `decode-metadata` :219-223, `schema:update-params` :225-235).
**Signature:** `(decode-metadata metadata) -> {:keys [storage-ref-id generated-by referer]} | nil`; `handle-persistence` dispatches on the `backend` string.
**Data Shape:** metadata is an OPEN Malli map (optional keys only): `storage-ref-id` uuid (backend-owned), `generated-by` string, `referer` string (importer-owned). The OLD closed schema `[:map {:closed true} [:storage-ref-id …]]` was DELETED from fdata.clj and replaced by the shared common schema — that widening is the porting point.

### Decisive source
```clojure
(= backend "storage")
(let [sobject  (sto/put-object! storage {...})
      metadata (-> (:metadata params)
                   (assoc :storage-ref-id (:id sobject)))
      params   (-> params (assoc :metadata metadata) (assoc :data nil))]
  (upsert-in-database cfg params))

(= backend "db")
(let [metadata (dissoc (:metadata params) :storage-ref-id)
      params   (assoc params :metadata metadata)]
  (upsert-in-database cfg params))
;; decode side:
(defn decode-metadata [metadata]
  (some-> metadata (db/decode-json-pgobject) (ctf/decode-file-metadata)))
```

**Flow:** storage backend MERGES importer-provenance with its own `storage-ref-id` and nulls the inline `:data` (bytes live in object storage); db backend strips any stale `storage-ref-id` but KEEPS provenance keys (previously it dropped metadata wholesale); legacy-db keeps its old behavior. Read path decodes pgobject JSON then validates through the shared decoder — unknown keys are tolerated by the open map, so future metadata fields don't break old readers.
**Invariant:** `:metadata` travels with the file row, not the blob; the storage pointer is written by exactly one writer (the storage branch) and stripped everywhere else, so a db-backend file can never carry a dangling ref. Import writes provenance via `d/without-nils` so absent manifest fields never become explicit nils.
**Probe:** direct test `backend/test/backend_tests/binfile_test.clj` `import-binfile-v3-persists-manifest-metadata` (:224-245) — export→import roundtrip yields `(get-in imported [:metadata :referer])` = `"penpot"` and a non-nil `:generated-by`. Grep anchor: `grep -c 'schema:file-metadata' common/src/app/common/types/file.cljc` → 3 (:91 def, :115 file-schema reference, :133 doc-comment mention).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"decode-file-metadata schema file-metadata","limit":5,"detail":"ids"}'
```
(rank 1-3 hit `decode-file-metadata` :133-134, `fdata.decode-metadata` :219-223, `schema:file-metadata` :91-95.)

## Verdict
Adopt the open optional-key metadata envelope + per-backend merge/strip discipline + shared common-level decoder. Adapt key names and the pgobject decode to your persistence stack. Omit the legacy-db branch if you have no dual-backend migration window.
