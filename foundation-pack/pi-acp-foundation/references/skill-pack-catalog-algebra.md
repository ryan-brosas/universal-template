<!-- capsule-v2 -->
# Skill-pack catalog algebra — how do you keep a growing skill/leaf catalog structurally honest in one pure-read gate?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A catalog of prompt-skills grows: packs (routers) own hidden leaves, some skills are always-visible core, and a generated manifest mirrors membership. Every axis can drift independently — an unassigned leaf, a leaf in two packs, a router whose member list disagrees with the catalog, a hidden leaf that became model-visible, visible metadata bloating past the context budget. How do you make ALL of that fail one fast pure-read check?

## Membership / visibility / parity / budget algebra over frontmatter + catalog JSON
**Path/Symbol:** `scripts/validate-skill-packs.mjs` (whole, 274L) — constants :15-24, frontmatter parse :44-79, catalog schema :108-118, router detection :120-124, hygiene :128-146, trigger budget :149-156, parity :159-183, membership :186-207, visibility :210-222, context budget :225-230, manifest re-derivation :233-250, size accounting :253-258. Shared kernel: `findSkillFiles` from `scripts/lib/validate-common.mjs` (cited by smoke-inventory-discipline.md). Manifest twin: references/generated-manifest-drift.md.
**Signature:** `node scripts/validate-skill-packs.mjs [root]` (root defaults to repo root; read-only; `[skip]` exit 0 when `.pi/skills` is absent).
**Data Shape:** discovered = every SKILL.md under `.pi/skills` parsed for frontmatter (`name`, quote-aware `description`, `disable-model-invocation`); routers = files whose GRANDPARENT is the skills root AND whose parent dir starts with `pack-` (directory shape, not metadata); leaves = the rest. Catalog = `packs.json` `{version:number, maxAutoLoadedLeafSkills:int≥1, maxVisibleMetadataTokens:int≥1, visibleCore:string[], packs:[{id:'pack-*', members:string[]}]}`. Failure channels are partitioned (hygiene / trigger / parity / metadata / manifest) but all feed one `errors[]` → exit 1.

### Decisive source
```js
// Membership: every leaf in exactly one pack (or visibleCore).
for (const [name, packsOf] of memberOf) {
  if (packsOf.length > 1) fail(`duplicate primary membership: "${name}" in ${packsOf.join(', ')} (exactly one pack)`)
}
for (const leaf of leaves) {
  const inPack = memberOf.get(leaf.name) || []
  const inCore = core.includes(leaf.name)
  if (inPack.length === 0 && !inCore)
    fail(`unassigned leaf "${leaf.name}" at ${leaf.rel}: add it to exactly one pack in packs.json or to visibleCore`)
  if (inCore && inPack.length > 0) fail(`"${leaf.name}" is in visibleCore AND in a pack; choose one`)
}
// Visibility: routers and core visible, leaves hidden.
for (const leaf of leaves) {
  if (!core.includes(leaf.name) && !leaf.disabled)
    fail(`leaf "${leaf.name}" at ${leaf.rel} is model-visible; add "disable-model-invocation: true" to its frontmatter`)
}
// Context budget: visible metadata stays under the catalog limit.
const metaTokens = Math.ceil(metaChars / 4)
if (metaTokens > BUDGET) fail(`visible metadata ${metaTokens} tokens exceeds budget ${BUDGET} ...`)
```

**Flow:** (1) validate the catalog schema itself (version number, integer budgets ≥1, ≥1 pack, `pack-` id prefix, members arrays); (2) hygiene over EVERY discovered skill — description required (the host does not load skills without one), ≤1024 chars (Agent Skills limit), unquoted `": "` in description fails (it would parse as a YAML mapping), name grammar `^[a-z0-9]+(-[a-z0-9]+)*$` ≤64 chars, frontmatter fields whitelisted, stale-harness-vocabulary regex (`TaskCreate|TaskUpdate|ask_user_question|web_fetch|grepsearch|superpi`) banned; (3) trigger-first budget for HIDDEN leaves only (visibleCore exempt): description must start `Use when ` and stay ≤240 chars; (4) catalog↔router parity — each catalog pack needs a router named after it, router description must EQUAL the catalog pack description (both unquoted), and the router's list markers (`[-|] name [:|]` lines) must match `members` bidirectionally (missing AND extra both fail), with a 190-word router body budget; (5) membership algebra — every declared member exists on disk, exactly-one-pack per leaf, no unassigned leaves, visibleCore XOR pack, every visibleCore entry exists on disk; (6) visibility rules — routers and core must NOT set disable-model-invocation, non-core leaves MUST; (7) context budget — routers + core names+descriptions, chars/4 ceil = tokens ≤ maxVisibleMetadataTokens; (8) manifest drift — independently re-derive the retained ledger and compare (see generated-manifest-drift.md); (9) size accounting — report max router words, WARN (not fail) leaves >600 words with "move detail to references/".
**Invariant:** exactly-one ownership (pack OR visibleCore, never both, never neither); visibility is a function of role (router/core visible, leaf hidden); the catalog JSON and the router markdown can never disagree on ids, descriptions, or member lists; the always-visible metadata surface has a hard token budget owned by the catalog itself. The check is pure-read (no writes, no spawn) so it gates cheaply in the canonical chain.
**Probe:** LIVE this pass: `node scripts/validate-skill-packs.mjs` on this checkout → `[skip] .pi/skills is not in this checkout; skill-pack checks run in the development tree`, exit 0 (`.pi/skills` is gitignored dev-tree state, absent here). No direct unit test exists for the validator; the negative paths are pinned by source logic only. The manifest-parity block's positive consumer is sync-skill-manifest.mjs --check (same chain position in scripts/check.mjs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "validate-skill-packs packs.json visibleCore disable-model-invocation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole algebra shape: directory-shape router detection (no metadata to lie about), exactly-one-membership with explicit XOR against the always-visible set, bidirectional parity diffs (missing AND extra), role-driven visibility rules, a token budget for the visible surface expressed in the catalog (not hardcoded in the validator), trigger-first + char-budget descriptions for hidden entries, and warn-not-fail for size growth. Adapt the budgets (1024/240/190/600), the name grammar, the stale-vocabulary regex, and the `pack-` prefix to your catalog. Omit the specific pack ids and the Agent-Skills-specific field whitelist unless your host enforces the same spec. Caveat: no direct test pins any negative branch; the gate's authority is its presence in the canonical check chain (canonical-check-command.md).
