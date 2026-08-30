<!-- capsule-v2 -->
# File-migrations registry kernel — how does a .penpot file declare what already ran, and what applies the rest?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (`main` fast-forward of pin dd6b521b, zero conflicts); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How do you apply an ordered backlog of data migrations to a document exactly once, when the document may predate the migration ledger itself?

## Migration ledger = append-only ordered-set on the file
**Path/Symbol:** `common/src/app/common/files/migrations.cljc` (`need-migration?` :52-59, `migrate` :64-86, `generate-migrations-from-version` :88-97, `migrate-file` :99-128, `migrated?` :130-132, `available-migrations` :1981-2063, `defmulti migrate-data` :48-50).
**Signature:** `(migrate-file file libs) -> file'` ; `(migrate file libs) -> file'` ; `(need-migration? file) -> boolean` ; `(migrated? file) -> boolean` (reads `meta ::migrated`).
**Data Shape:** file has `:version` int (current format version lives ONLY on the file, never in data), `:migrations` ordered-set of id strings (81 entries, `"legacy-N"` … `"0025-repair-empty-text-content"`), `:data`. `libs` is a delayed/ref of library files injected into data only DURING reduction. Each migration is a multimethod case `(defmethod migrate-data "<id>" [data _] -> data')`.

### Decisive source
```clojure
(defn migrate-file
  [file libs]
  (binding [cfeat/*new* (atom #{})]
    (let [version     (or (:version file) (-> file :data :version))
          migrations  (not-empty (get file :migrations))
          file        (-> file
                          (assoc :version cfd/version)
                          (assoc :migrations
                                 (if migrations
                                   migrations
                                   (generate-migrations-from-version version)))
                          (update :features cfeat/migrate-legacy-features)
                          (migrate libs)
                          (update :features (fnil into #{}) (deref cfeat/*new*)))]
      ;; NOTE: When we have no previous migrations, we report all
      ;; migrations as migrated in order to correctly persist them all
      ;; and not only the really applied migrations
      (if (not migrations)
        (vary-meta file assoc ::migrated (:migrations file))
        file))))
```

**Flow:** `migrate-file` seeds `:migrations` from the numeric version when absent (`generate-migrations-from-version`: `take-while #(<= % version)` over 1..current, mapped to `"legacy-N"`, filtered to registered ids) → `migrate` computes `diff = available-migrations − (:migrations file)`, folds `(reduce migrate-data data diff)` with `:libs` mounted, then `assoc :id`, `dissoc :version :libs` from data, runs `ctf/check-file-data`, and unions `diff` back into `:migrations` while stamping `::migrated` metadata → callers persist only when `(migrated? file)`.
**Invariant:** The ledger is append-only set-union (`update :migrations set/union diff`) — a migration can never re-run once recorded, and `need-migration?` fires on EITHER a version mismatch OR any unregistered-but-listed id (`set/difference available-migrations (:migrations file)` non-empty means the file knows migrations this build doesn't have). A file with NO `:migrations` key gets the ENTIRE set marked migrated (deliberate bulk-persist semantics, comment :123-125) even though only the version-derived `legacy-N` subset actually ran — do not "fix" this asymmetry.
**Probe:** `common/test/common_tests/files_migrations_test.cljc` `generic-migration-subsystem-1` (:19-28) — with `available-migrations` redefs'd to `test/1..3` and `check-file-data` identity, a file carrying `:migrations #{test/1}` and `{:sum 1}` comes back with all three ids and `:sum 3`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"migrate-file","limit":5,"detail":"ids"}'
```
(rank 2 resolves `common.src.app.common.files.migrations.migrate-file Function common/src/app/common/files/migrations.cljc 99-128`; rank 1 is the backend binfile twin — route by Source line.)

## Verdict
Adopt the ordered-set ledger + version-seeding + fold-once design and the `::migrated` metadata channel (pure, runtime-agnostic). Adapt the feature-flag coupling (`cfeat/*new*` binding, `migrate-legacy-features`) to your own feature system. Omit the specific 81-entry registry contents — they are Penpot document-history, not reusable behavior.
