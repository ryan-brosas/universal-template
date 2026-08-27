---
purpose: "Canonical foundation skill anatomy: one leaf template and one capsule-v2 template for every foundation."
---

# Foundation skill anatomy

A foundation is a lean retrieval surface backed by proven code. The source repo and its direct tests are ground truth; a reference supplies only the code-shaped context needed to reuse a confirmed seam safely.

## One canonical pair
Copy the foundation leaf and capsule exactly from `references/foundation-templates.md`. The canonical shared copies live at `~/.agents/templates/foundation-skill.md` and `~/.agents/templates/foundation-capsule.md` (template-only library assets, not slash-command render targets); host mirrors such as `/home/utopia/.dsh/template/work/project/foundation-*.md` are derived copies. There is no second leaf or reference layout.

```
skills/<repo>-foundation/
  SKILL.md                # canonical leaf: loader + map + provenance + boundaries
  references/<seam>.md    # one capsule-v2 per porting question
```
Work one source repo at a time; count and length are set by reusable contracts.

## Leaf placement
The fixed `SKILL.md` order is `Use this for` → `Load the matching source dump` → `Capsule map` → `Extending the foundation` → `Provenance` → `Full view (memory graph)` → `Boundaries`.
The leaf routes, catalogs each capsule once, groups by capability, records graph identity/freshness, and bounds adoption. It never repeats decisive excerpts, test mechanics, module status, wave timing, or an exhaustive repository census; those live in capsules or the durable work record.

## Reference placement
Every new or substantively rewritten normal reference starts with `<!-- capsule-v2 -->` and follows the canonical `Source` → question → `Path/Symbol` → `Signature` → `Data Shape` → labelled `Decisive source` → `Flow` → `Invariant` → direct-test `Probe` → `Retrieve` (`search_graph`) → `Verdict` order.

The graph selects the seam, but source overrides it. If a direct test is absent or excluded, record the caveat in the verdict—never invent coverage. Each capsule answers one porting question and carries only the excerpt needed to prevent a likely wrong port.

## Mechanical checks
Direct inspection establishes capsule evidence, leaf↔reference parity, provenance, and scaffold/padding exclusions. Prove the authoring change RED first, then record source/test, graph coverage, retrieval, and final-diff evidence.
