<!-- capsule-v2 -->
# view-section copy inheritance — when duplicating a view, whose section wins?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** A view duplicate should land where its source lives — but which caller overrides exist, and how does explicit-null differ from unset?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/models/View.ts:duplicateView` (:3006 allowlist entry `'fk_view_section_id'`; inheritance :3039–:3044).
**Signature:** EE-gated branch inside duplicateView: `if (isEE && copyFromView && insertObj.fk_view_section_id === undefined)` → inherit.
**Data Shape:** allowed-fields list gains 'fk_view_section_id'; tri-state caller input: undefined=inherit from source, null=top level, value=that section.

### Decisive source
```ts
// When duplicating a view, keep the copy inside the same section as the
// source view. A caller-supplied value always wins — including `null`,
// which means "create at top level, not in the source's section".
if (isEE && copyFromView && insertObj.fk_view_section_id === undefined) {
  insertObj.fk_view_section_id = copyFromView.fk_view_section_id;
}
```

**Flow:** add fk_view_section_id to the copy allowlist → after loading copy_from_view, fill the section ONLY when the caller left it strictly undefined → proceed with normal insert.
**Invariant:** (1) undefined ≠ null: null is an EXPLICIT choice of top-level and must win over inheritance — using falsy checks here would make explicit-null impossible to express. (2) Inheritance reads the ALREADY-LOADED copyFromView (no extra fetch). (3) The allowlist gates the field before this branch; adding inheritance without the allowlist entry would drop the key entirely. (4) EE-gated like the sections feature itself.
**Probe:** `sed -n '3036,3045p' packages/nocodb/src/models/View.ts` shows allowlist entry + inheritance block verbatim. No unit runner for View model (caveat).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "duplicateView fk_view_section_id View copy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the undefined-vs-null override ladder; adapt feature gating; omit if host has no view-section concept.
