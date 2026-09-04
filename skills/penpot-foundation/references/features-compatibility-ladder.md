<!-- capsule-v2 -->
# Feature-gate compatibility ladder — how does a backend refuse a file/client/team whose feature set it can't serve?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How do you model optional document capabilities so that opening, pasting, and team-copying all fail safe with named codes instead of corrupting data?

## Feature taxonomy + five check funnels
**Path/Symbol:** `common/src/app/common/features.cljc` whole file (`supported-features` :45-61, `default-features` :64-73, `frontend-only-features` :79-87, `backend-only-features` :91-93, `no-team-inheritable-features` :97-99, `no-migration-features` :105-113, `flag->feature` :124-140, `migrate-legacy-features` :142-158, `get-team-enabled-features` :174-184, `check-client-features!` :186-205, `check-supported-features!` :207-218, `check-file-features!` :220-259, `check-teams-compatibility!` :261-295, `check-paste-features!` :298-336).
**Signature:** `(check-file-features! enabled-features file-features) -> enabled-features | raise`; same shape for the other four checkers.
**Data Shape:** features are plain string sets (`"fdata/objects-map"`, `"components/v2"`, …). Files persist their set in `:features`; teams too; runtime flags map kebab keywords → features via a `case` table returning nil for unknown flags.

### Decisive source
```clojure
(let [file-features (into #{} xf-remove-ephimeral file-features)
      not-supported (-> enabled-features
                        (set/difference file-features)
                        (set/difference no-migration-features))]
  (when-let [not-supported (first not-supported)]
    (ex/raise :type :restriction :code :file-feature-mismatch
              :feature not-supported
              :hint (str/ffmt "enabled feature '%' not present in file (missing migration)" not-supported)))
  ;; ...then the reverse direction:
  (when-not (contains? file-features "components/v2")
    (ex/raise :type :restriction :code :file-in-components-v1 ...))
  (let [not-supported (-> file-features
                          (set/difference enabled-features)
                          (set/difference backend-only-features)
                          (set/difference frontend-only-features))]))
```

**Flow:** every funnel is a directional set-difference minus a forgiveness class: (1) `check-supported-features!` — an imported file's features ⊆ this build's `supported-features`, else `:feature-not-supported`; (2) `check-file-features!` — backend-enabled ∖ file must be within `no-migration-features` else `:file-feature-mismatch` ("missing migration"), then hard-refuse v1 components, then file ∖ enabled must be within frontend-only+backend-only; (3) `check-client-features!` — same shape for the browser's declared set; (4) `check-teams-compatibility!` — bidirectional team diff with `ephimeral/migration` short-circuit (`:migration-in-progress`) and forgiveness = no-migration ∪ default; (5) `check-paste-features!` — clipboard content checked in BOTH directions with its own codes.
**Invariant:** `ephimeral/*` prefixed features never participate in comparisons (`xf-remove-ephimeral`) except the explicit migration-in-progress gate. The forgiveness classes ARE the design: a missing feature only blocks when migrating the file would be REQUIRED to serve it. Errors carry the offending feature name — clients can degrade or explain precisely.
**Probe:** deterministic greps from repo root (counts re-derived at pin): `grep -c 'ex/raise' common/src/app/common/features.cljc` → 12; `grep -c 'no-migration-features)' common/src/app/common/features.cljc` → 5 (uses at :183/:232/:275/:287/:309; the def itself has no trailing paren so it doesn't count — don't "fix" that); `grep -c '"components/v2"' common/src/app/common/features.cljc` → 3.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"check-file-features","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the taxonomy (supported/default/frontend-only/backend-only/no-migration) plus directional-difference-with-forgiveness checking and named error codes. Adapt feature names and the flag→feature case table to your product. Omit the ephimeral migration-in-progress workflow if you have no server-side team migration.
