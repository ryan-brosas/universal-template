<!-- capsule-v2 -->
# Workspace file-stats audit event — how do you emit one enriched telemetry event per workspace open, after all async deps settle?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (47d599f); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** Where in an event-driven frontend do you compute document statistics so counts are complete but the event fires exactly once?

## Single-pass stats + libraries-resolved gate
**Path/Symbol:** `frontend/src/app/main/data/workspace.cljs` (`compute-shape-stats` :271-283, `compute-file-stats` :285-310, `emit-workspace-file-stats` :312-322, emission gate :479-483) + direct test `frontend/test/frontend_tests/data/workspace_stats_test.cljs` (87L, 5 deftests).
**Signature:** `(compute-file-stats state file-id) -> {:num-pages :num-shapes :avg-shapes-per-page :max-shapes-per-page :num-components :num-linked-libraries :is-library :num-tokens}`.
**Data Shape:** reads re-frame-like `state`: `:files` index, file `:data` (`:pages-index`, `:pages`, `:components`, `:tokens-lib`), `refs/select-libraries` map (id→file; includes the file itself).

### Decisive source
```clojure
n-components   (reduce-kv (fn [n _ c] (if (:deleted c) n (inc n)))
                          0 (:components file-data))
n-linked-libs  (dec (count libraries))
...
:num-linked-libraries (max 0 n-linked-libs)
:is-library (:is-shared file)

;; emission gate inside the initialize watch stream:
(->> stream
     (rx/filter (ptk/type? ::all-libraries-resolved))
     (rx/take 1)
     (rx/map #(emit-workspace-file-stats file-id team-id)))
```

**Flow:** the gate's upstream producer is `fetch-libraries` (:179-212): it rx-concats the library-fetch chain (libraries-fetched → per-library get-file + resolve-file → thumbnails) and then UNCONDITIONALLY appends `(ptk/data-event ::all-libraries-resolved …)` at :211 — so the marker fires when fetching is DONE, not when each item lands, and it also fires on total failure (the concat still emits). The stats event re-reads state at FIRE time (not at registration time) and emits `{stats + ::ev/name "open-workspace-file" ::ev/origin "workspace" :file-id :team-id}` — gated with `(rx/filter (ptk/type? ::all-libraries-resolved))` + `(rx/take 1)` (:480-483) so exactly one event per workspace session, AFTER library fetches settle (that's why `num-linked-libraries` is trustworthy).
**Invariant:** avg uses `(mth/round (/ num-shapes n-pages))` guarded by `(pos? n-pages)` else 0 — never a divide-by-zero. The gate ordering (libraries before stats) is load-bearing; computing at `workspace-initialized` would under-count links.
**Probe:** direct tests pin all edge cases: `compute-file-stats-empty-file` (:26-42) asserts every key present and non-negative on a bare file; `compute-file-stats-with-tokens` (:68-81) builds a real tokens-lib via `ctob/add-set` and expects `:num-tokens 1`; `compute-file-stats-multiple-pages` (:83-92) → `:num-pages 3`. Grep anchor from repo root: `grep -c 'all-libraries-resolved' frontend/src/app/main/data/workspace.cljs` → 2 (:211 producer, :481 consumer); `grep -c 'defn compute' frontend/src/app/main/data/workspace.cljs` → 1 (`compute-file-stats`; `compute-shape-stats` is a private `defn-` at :271).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"compute-file-stats","limit":4,"detail":"ids"}'
```
(rank 1-2: `compute-file-stats` 285-310, `compute-shape-stats` 271-283.)

## Verdict
Adopt: single-pass accumulation, deleted-exclusion, self-inclusive-library −1 with clamp, and the settle-then-emit-once rx gate. Adapt to your state container and telemetry naming. Omit Penpot's plugin/MCP initialization streams around it.
