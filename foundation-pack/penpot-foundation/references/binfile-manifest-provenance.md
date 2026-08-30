<!-- capsule-v2 -->
# Binfile manifest referer→metadata bridge — how do you persist import provenance from an archive manifest onto every imported file?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (47d599f); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How does one manifest-level fact (who generated this .penpot export) become a per-file DB field, including backward compatibility with an older manifest spelling?

## Manifest schema + import-time stamping
**Path/Symbol:** `backend/src/app/binfile/v3.clj` (`schema:manifest` :54-59 with `[:referer {:optional true} :string]` :58 and `generated-by` :59; export writer :392-398; `read-manifest` :465-470; `import-file` :736-814 with metadata assoc :804-807) + `backend/src/app/binfile/common.clj` (`file->public-data`-style strip adds `(dissoc :metadata)` at :726).
**Signature:** `(import-file cfg {file-id :id file-name :name}) -> file` where `cfg` now carries `::manifest`.
**Data Shape:** manifest.json in the zip root: `{... :referer "penpot" :generated-by "penpot/1.x" :files [...]}`. Imported file rows gain `:metadata {:generated-by … :referer …}` (nils removed via `d/without-nils`).

### Decisive source
```clojure
(defn- import-file
  [{:keys [::db/conn ::bfc/project-id ::manifest] :as cfg} {file-id :id file-name :name}]
  ...
  (assoc :metadata (d/without-nils
                     {:generated-by (get manifest :generated-by)
                      :referer (or (get manifest :referer) (get manifest :refer))}))
;; export side (same commit renamed the key):
:params {:type "penpot/export-files"
         :version 1
         :generated-by (str "penpot/" (:full cf/version))
         :referer "penpot"
         ...}
```

**Flow:** export writes `manifest.json` first among zip entries → import reads it once (`read-manifest`, kebab-keyed JSON decode through `schema:manifest`) → the parsed manifest rides the config (`::manifest`) into each per-file import → provenance stamped on every file row. The compatibility clause `(or (get manifest :referer) (get manifest :refer))` accepts archives written by builds that misspelled the key as `:refer` — old exports still import cleanly into new servers.
**Invariant:** The public file serializer STRIPS `:metadata` (:723-726 dissoc added in same commit) so provenance never round-trips back out through re-export — it is server-local telemetry data, not document content. `without-nils` keeps absent keys absent rather than null.
**Probe:** direct test `backend/test/backend_tests/binfile_test.clj` `import-binfile-v3-persists-manifest-metadata` (:224-245). Deterministic greps from repo root: `grep -c ':referer' backend/src/app/binfile/v3.clj` → 3 (schema, export writer, import or-clause); `grep -n 'get manifest :refer)' backend/src/app/binfile/v3.clj` → line 806 only.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"import-file manifest referer metadata binfile v3","limit":5,"detail":"ids"}'
```
(rank 1: `binfile.v3.import-file Function backend/src/app/binfile/v3.clj 736-814`.)

## Verdict
Adopt the pattern: versioned manifest schema → config-carried context → per-item stamping with legacy-key fallback → strip-on-export. Adapt the zip/binfile specifics to your archive format. Omit Penpot's relations/index plumbing around the manifest.
