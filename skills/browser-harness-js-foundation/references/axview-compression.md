<!-- capsule-v2 -->
# axView compression — how does a hundreds-of-thousands-token raw AX dump become an actionable ~20K-token tree?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Which nodes survive the projection, and what are the traversal traps a reimplementation gets wrong?

## Survive-set with ancestor rescue, ignored-bubbling, name-equals-subtree coalescing, DFS ref numbering
**Path/Symbol:** `skills/cdp/sdk/axview.ts:axView` (:170-332); role sets `LEAF`/`INT`/`LM`/`DROP` (:47-121); sensitive redaction `SENSITIVE_NAME_RE` + `isSensitive` (:123-146).
**Signature:** `axView(nodes: any[], opts?: { refs?, interactive?, maxDepth?, redactSensitive?, locators? }): string`.
**Data Shape:** measured 886K → 22K tokens (Wikipedia), 210K → 7K (app page). Output = indented lines `[n] role "name" <flags> ="value"` + trailing `# refs -> backendDOMNodeId` map (`[1]=100 [2]=101 …`, newline-separated when locators carry spaces).

### Decisive source
```ts
const post = (n: any): boolean => {
  if (n.ignored) {                       // ignored wrappers BUBBLE: children may keep
    let c = false;
    for (const id of n.childIds || []) if (post(byId.get(id))) c = true;
    return c;
  }
  ...
  let keep = keepSelf(r, nameOf(n), interactive);
  let cs = false;
  for (const id of n.childIds || []) if (post(byId.get(id))) cs = true;
  if (cs) keep = true;                   // ancestors of kept descendants must survive so emit can reach them
  if (keep) survive.add(n.nodeId);
  return keep;
};
```
Coalescing pass: a node whose own name equals its subtree's joined StaticText keeps only the node line — `link "Donate"` swallows `StaticText "Donate"`. Refs number in emit order (DFS pre-order), first occurrence wins on duplicate nodeIds.

**Flow:** dedupe by nodeId keeping FIRST → find root (`RootWebArea` else first non-ignored) → post-order survive pass (LEAF never survives; DROP roles survive only via kept children or a name) → coalesce redundant text children → suppress value-bearing StaticText under sensitive textboxes (Chrome nests the bullet mask under generic wrappers, not as a direct child) → DFS emit skipping suppressed/dropped, bubbling ignored nodes at the parent depth → append ref map (+ optional `loc=role:R["N"]` per ref).
**Invariant:** (1) A naive "skip ignored" walk discards the ENTIRE subtree — real pages nest everything under `ignored:true` none/generic wrappers; you must recurse through them. (2) The ancestor-rescue rule is what keeps structure without reintroducing bulk prose (in interactive mode pure-StaticText children never keep). (3) Duplicate virtual nodeIds occur — first-wins or your map double-books. (4) Refs are emitted in DFS pre-order and renumber every snapshot; `parseAxRefs`/`parseAxLocators` regex-matchAll over the tail tolerate both one-line and multi-line maps.
**Probe:** direct tests `skills/cdp/sdk/axview.test.ts` (:33-122): DFS ref/map order incl. child-before-sibling (`[3]` = navigation's child "Log in"), locator emission + round-trips, `refs:false`, interactive mode dropping headings/StaticText.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "axView", limit: 5, fields: ["signature", "name", "file"] });
// resolves axview.axView @ axview.ts:170-332
```

## Verdict
Adopt the survive/bubble/coalesce pipeline wholesale when compressing accessibility trees for model context; adapt role sets to your product's notion of actionable; omit the locators section only if you also port its consumer (ax-locator-resolution capsule). Table grids flatten by design — drop to raw `getFullAXTree` when row/column position is signal (documented boundary, snapshot.md).
