<!-- capsule-v2 -->
# Group & mask selrect regeneration — how does a container's geometry track its transformed children?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** When children move/resize/rotate, how do you recompute a group's bounding geometry without double-applying the group's own transform — and who owns a mask's bounds?

## Children-in-group-space round trip + mask-first-child ownership
**Path/Symbol:** `common/src/app/common/geom/shapes/transforms.cljc` (`update-group-selrect` :408-444, `update-group-viewbox` :390-406, `update-mask-selrect` :446-457, `update-shapes-geometry` :459-481, `apply-children-modifiers` :542-558, `apply-group-modifiers` :560-582).
**Signature:** `(update-group-selrect group children)` → group' ; `(update-mask-selrect masked-group children)` → group' ; `(update-shapes-geometry objects ids)` → objects'.
**Data Shape:** group has `:shapes` (child id vector), `:transform`, `:transform-inverse`, optional `:svg-viewbox` (SVG-import groups only); children passed as full shape maps.

### Decisive source
```clojure
(defn update-group-selrect [group children]
  (let [points (->> children (mapcat :points))
        shape-center (gco/points->center points)
        points (if (empty? points) (:points group) points) ;; Fixed problem with empty groups
        base-points  (gco/transform-points points shape-center (:transform-inverse group (gmt/matrix)))
        new-points   (-> (grc/points->rect base-points)
                         (grc/rect->points)
                         (gco/transform-points shape-center (:transform group (gmt/matrix))))
        ...
        (-> group
            (update-group-viewbox new-selrect)
            (assoc :selrect new-selrect)
            (assoc :points new-points)
            (assoc :flip-x false)   ;; regenerated from children => flips cleared
            (assoc :flip-y false)
            (apply-transform (gmt/matrix)))))
```

**Flow:** union all child corner points → map them through the group's transform-INVERSE into local space → collapse to AABB → re-expand to corners → apply the group's transform back → that IS the new selrect+points. SVG-import viewboxes ride along via per-side deltas (:394-397). Masked groups do NOT union: they ADOPT the first child's selrect/points/x/y/w/h/flips wholesale (`update-mask-selrect`). The dispatcher `update-shapes-geometry` routes by shape kind: mask→adopt, bool→`path/update-bool-shape`, group→regenerate, else untouched.
**Invariant:** (1) The inverse-transform round trip is what prevents DOUBLE application: children store coordinates already in world space; naive AABB over them bakes the group's rotation in as shear. (2) Regeneration CLEARS flip flags — a rebuilt-from-children rect cannot be "flipped" (grep pin: `(assoc :flip-x false)` exactly 1 site). (3) Empty-group guard falls back to the group's OWN stale points with an explicit source comment ("Should not happen (but it does)") — keep it. (4) Modifier propagation during interactive drags mirrors the same scoping: `apply-group-modifiers` passes parent modifiers down ONLY when `propagate?` is true (:565-582), and bools take `transform-shape` while masks take adoption — three sibling kinds, three different rules.
**Probe:** `common/test/common_tests/geom_shapes_test.cljc` pins the dispatcher plane indirectly via transform-shapes suite; direct census pins: `grep -cF ':svg-viewbox' common/src/app/common/geom/shapes/transforms.cljc` → 1 write site ; `grep -c 'Fixed problem with empty groups' <same>` → 1 ; `grep -cF '(assoc :flip-x false)' <same>` → 1.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"update-group-selrect svg-viewbox mask","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the inverse-round-trip regeneration, the mask-adopts-first-child rule, and flip-clearing on regeneration. Adapt viewbox delta bookkeeping if you have no SVG-import concept. Omit the bool-shape branch internals (owned by the path/bool plane).
