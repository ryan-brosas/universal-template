<!-- capsule-v2 -->
# Anchor-hub collapse — how do server registrations and client calls of one route meet at a single graph node?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** "POST /auth/login" appears at the server registration AND in every client call — one feature or N nodes? How are hub edges weighted so a route consumed everywhere doesn't become a gravity well?

## One node per label, sqrt-decayed site conductance
**Path/Symbol:** `src/core/build.ts:assembleGraphWithIndex` anchor plane (:1015-1053); hub consumption `ops.ts:sketch` production anchors (:624-693), `render.ts` ⚑ lines.
**Signature:** internal to `assembleGraphWithIndex(root, files, factsMap): Promise<{graph, joinIndex}>`.
**Data Shape:** All drafts grouped by normalized anchor id (`"<VERB> <normalized-path>"`). Hub node id = `anchor:<label>`, kind `"anchor"`, sig carries `(△ discovered)` prefix and `<label> (N sites)`. Edge to each handler `w = (hubImplicit ? 0.5 : 1)/√sites`; multi-file features also bind their files `w = 0.35/√filesOf.length` when 2..12 files.

### Decisive source
```ts
// Anchors: ONE node per feature route, not per site. Server registration
// and every client call of "POST /auth/login" are occurrences of the same
// feature; the anchor hub is where they meet. Site conductance decays with
// sqrt(count) so a route consumed everywhere doesn't become a gravity well.
const hubImplicit = sites.every((s) => s.implicit === true);
// A hub is implicit only when EVERY site came from a discovered rule — a
// match by any real rule upgrades it back to first-class instantly.
const w = (hubImplicit ? 0.5 : 1) / Math.sqrt(sites.length);
for (const s of sites) {
  const handler = seen.get(s.nodeId) ?? fileIdx.get(s.file)!;
  pushEdge(idx, handler, "anchors", w);
}
```

**Flow:** collect per-file anchor drafts → group by id → emit ONE hub node per unique route → wire hub→handler-symbol edges for every site (fallback: the file node) → optional hub→file hood edges → sketch then groups by hub closure (`closureFor(i) = [i, ...adjacency]`), summing field mass per feature and collapsing test-scope hubs into a single discounted "tests/fixtures" line.
**Invariant:** Identity is the NORMALIZED label, not the call site — gin `:id`, OpenAPI `{id}`, and template `${id}` occurrences all join one hub via normalizeLiteral. First-class evidence anywhere in the repo upgrades the whole hub (per-site `every(implicit)` rule). The sqrt decay is what keeps a ubiquitous client call from dominating diffusion; the file-hood cap (≤12) keeps umbrella routes from gluing unrelated directories.
**Probe:** `tests/extract.test.ts` anchor suites pin the ids ("GET /api/users/{*}" from Go registration; template-literal and f-string client calls land on the same `{*}` shape); `tests/discover.test.ts` integration pins implicit half-weight hubs + first-class non-implicit coexistence; `tests/ops.test.ts` sketch renders "⚑ GET /api/users/{*}".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "anchor hub draftsByLabel implicit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt site-collapsed feature hubs with sqrt-conductance decay, normalized-label identity, file hoods with the ≤12 cap, and all-sites-implicit probation. Adapt the weight constants after measuring your own cascade masses. Omit nothing else.
