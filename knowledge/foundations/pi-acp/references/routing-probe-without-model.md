<!-- capsule-v2 -->
# Routing probe without a model — how do you test agent skill-ROUTING decisions without running the model?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A host loads skills by matching a task against each skill's `description` (trigger-first prose). Routing quality therefore lives ENTIRELY in description text — but testing it naively means running the model per task, which is slow, nondeterministic, and costs money. How do you pin routing behavior deterministically?

## Task cases as data, checked against the description surface the model actually sees
**Path/Symbol:** `scripts/probe-skill-routing.mjs` (whole, 146L) — case table :33-128, per-case checks :130-140, two-leaf rule prose check :141-146 (pack-backend + pack-toolchains routers), direct-execution invariant :147-151 (task-scoped-execution leaf). Catalog source: `.pi/skills/packs.json` (dev-tree state, gitignored).
**Signature:** `node scripts/probe-skill-routing.mjs` (no args; `[skip]` exit 0 when `.pi/skills` absent; read-only).
**Data Shape:** each case = `{task: string (human task phrasing), expect: string[] (leaf names that must be selectable), keywords: string[] (per-expected-leaf keyword that must appear in its description), max: number (selection cap for the task)}` — 21 cases at this pin. Description extraction re-parses frontmatter (`description:` line, quote-stripped) from each expected leaf's SKILL.md.

### Decisive source
```js
for (const c of cases) {
  const problems = []
  if (c.expect.length > c.max) problems.push(`expects ${c.expect.length} leaves, max ${c.max}`)
  const packs = c.expect.map(n => packOf.get(n))
  const missing = c.expect.filter((n, i) => !packs[i])
  if (missing.length) problems.push('missing from catalog: ' + missing.join(', '))
  if (c.expect.length > 1 && new Set(packs).size !== c.expect.length)
    problems.push('leaves share a pack: ' + c.expect.join(', '))
  for (const [i, name] of c.expect.entries()) {
    if (!packs[i]) continue
    const d = description(name).toLowerCase()
    if (!d.startsWith('use when')) problems.push(name + ' description is not trigger-first')
    if (!d.includes(c.keywords[i])) problems.push(name + ' description lacks keyword ' + c.keywords[i])
  }
  ...
}
// direct-execution invariant: task-scoped-execution must state the no-dispatch rule
const tse = readFileSync(join(skillsRoot, 'pack-delivery', 'task-scoped-execution', 'SKILL.md'), 'utf8')
if (/dispatch|delegate|subagent|agent/i.test(tse) && !/unsupported|never dispatch|no subagent/i.test(tse)) {
  failures++; console.log('FAIL task-scoped-execution lacks a no-dispatch rule')
}
```

**Flow:** for each case: (1) sanity — expect count ≤ max; (2) catalog membership — every expected leaf resolves to a pack; (3) CROSS-PACK separation — when a task expects multiple leaves, they must come from DISTINCT packs (this pins the two-leaf cross-pack selection rule: a task may pull at most one leaf per pack, so two leaves imply two packs); (4) surface checks — each expected leaf's description is trigger-first (lowercased `use when` prefix) AND contains its case keyword (the word the router/model would key on). Then two PROSE invariants: pack-backend and pack-toolchains routers must document "no more than two leaves", and task-scoped-execution may mention dispatch/delegate/subagent/agent ONLY negated (`unsupported|never dispatch|no subagent`) — a direct-execution-only skill must say so.
**Invariant:** the description text IS the routing surface — a case passes only if the exact words the model would match on are present, trigger-first, in the right leaves, with cross-pack expectations structurally separable. No model call, no network, no LLM judge: routing regressions (a rewritten description losing its keyword, a leaf moving packs, a second leaf added inside an already-selected pack) fail deterministically. The selection CAP (`max`) is pinned per task so a "select everything" drift is caught by arithmetic, not vibes.
**Probe:** LIVE this pass: `node scripts/probe-skill-routing.mjs` on this checkout → `[skip] .pi/skills is not in this checkout; routing probes run in the development tree`, exit 0. No direct unit test exists; the case table itself is the test fixture, co-located with the checker. Chain position: third gate in scripts/check.mjs (canonical-check-command.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "probe-skill-routing expect keywords max two-leaf", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the core move: encode routing expectations as DATA ({task, expect[], keywords[], max}) and verify them against the metadata surface the selector actually consumes — trigger-first prefix, keyword presence, cross-pack distinctness, per-task caps — instead of invoking the model. Add prose invariants for rules that live in router/leaf bodies (documented caps, negated capability mentions checked as positive-regex-AND-negation-regex). Adapt the case table to your catalog's real tasks, the trigger prefix to your host's convention, and the cap semantics to your loader. Omit the specific leaf names and the direct-execution invariant unless your runtime has the same delegation question. Caveat: this probes NECESSARY conditions of routability (the words are there), not SUFFICIENT ones (the model will pick them) — it is a regression gate, not a routing-quality measurement.
