<!-- capsule-v2 -->
# Repair-migration idiom — how do you write a one-shot data repair that is safe to re-run and safe to fail?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What shape must a document-repair transform take so a porter can add new ones without corrupting healthy documents?

## The 0024b exemplar: normalize → move → seed
**Path/Symbol:** `common/src/app/common/files/migrations.cljc` (`0024b-fix-stroke-cap-placement` :1842-1875) + direct test `common/test/common_tests/files_migrations_test.cljc` :30-75.
**Signature:** `(defmethod migrate-data "0024b-fix-stroke-cap-placement" [data _] -> data')`.
**Data Shape:** walks `:pages-index` (page-id→page) and `:components` via `d/update-vals`, then per-container `:objects` (shape-id→shape). Shape-level `:stroke-cap-start`/`:stroke-cap-end` move into `[:strokes 0 ...]`; string caps inside strokes are keywordized.

### Decisive source
```clojure
(fix-shape [shape]
  (let [cap-start (keyword (get shape :stroke-cap-start))
        cap-end   (keyword (get shape :stroke-cap-end))]
    (if (or (some? cap-start) (some? cap-end))
      (-> shape
          (dissoc :stroke-cap-start :stroke-cap-end)
          (cond-> (seq (:strokes shape))
            (update :strokes check-strokes)
            (and (some? cap-start) (seq (:strokes shape)))
            (assoc-in [:strokes 0 :stroke-cap-start] cap-start)
            (and (some? cap-end) (seq (:strokes shape)))
            (assoc-in [:strokes 0 :stroke-cap-end] cap-end)))
      shape)))
```

**Flow:** detect defect at shape level (`(or some? some?)`) → strip the misplaced attrs FIRST → only then write them into stroke 0, gated on `(seq (:strokes shape))`. A shape with caps but an EMPTY strokes vector loses the attrs entirely (test `migration-0024-fix-stroke-cap-no-strokes` pins exactly this: top-level keys removed even with no strokes — data loss of the orphaned attr beats persisting invalid schema).
**Invariant:** Idempotence by construction: after one run no shape carries level-0 caps, so a second run's `(or some? some?)` gate is false everywhere and the fold returns data unchanged. Repairs never throw on missing paths (`(get …)` defaulting nil); they degrade to keep-or-strip.
**Probe:** `files_migrations_test.cljc` `migration-0024b-fix-stroke-cap-placement` (:30-58) — shape with BOTH levels capped ends with nil at top level and `:round` on both strokes; plus `migration-0024-fix-stroke-cap-no-strokes` (:60-75).

## Sibling exemplars in the same file (same contract, different defects)
**Path/Symbol:** `"0022-normalize-component-root-and-resync"` :1826-1834 → `common/src/app/common/files/comp_processors.cljc` (`normalize-component-root` :41-63, `fix-missing-swap-slots` :65-99, `sync-component-id-with-ref-shape` :101-155); `"0025-repair-empty-text-content"` :1877-1979.
**Flow (0022):** normalization MUST precede the two fixers because `subcopy-head?` expects `:component-root` to be ABSENT while old files store explicit `false` (semantically identical for `instance-root?`, poison for the predicate) — ordering between migrations is load-bearing. Each fixer wraps its whole body in try/catch returning ORIGINAL file-data on ANY Throwable: a repair migration degrades to no-op rather than bricking file open. `normalize-component-root` reports `{:result :update :updated-shape …}` / `{:result :keep}` to the traversal protocol.
**Flow (0025):** three-level content-tree repair (root→paragraph-set→paragraph→span) where every level has the same cond ladder: nil-or-empty children → seed default; vector children → mapv child-repairer; anything else → replace with default. Invalid nodes are REPLACED not patched; root-level attributes are preserved via `select-keys content types.text/root-attrs` before merging defaults.
**Invariant (shared):** every repair is total over garbage input (never throws), idempotent (re-run = no-op), and scoped by a cheap predicate (`false?`, `subcopy-head?`, `text-shape?`) BEFORE any reconstruction work.
**Probe:** grep anchors: `grep -c 'try' common/src/app/common/files/comp_processors.cljc` → 3 (one per exported fixer); `sed -n '1826,1834p' common/src/app/common/files/migrations.cljc` shows the normalize→fix→sync order.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"normalize-component-root","limit":3,"detail":"ids"}'
```
(rank 1: `common.src.app.common.files.comp_processors.normalize-component-root Function comp_processors.cljc 41-63`.)

## Verdict
Adopt the four-part idiom: registry case + cheap predicate gate + strip-then-seed + try/catch-to-original. Adapt the traversal plumbing (`update-all-shapes` / `{:result :keep|:update|:remove}` protocol, `with-meta {:container container}` context) to your tree walker. Omit Penpot's specific shape/text schemas.
