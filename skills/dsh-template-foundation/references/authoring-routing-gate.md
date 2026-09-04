<!-- capsule-v2 -->
# Authoring-routing gate — how does a checker force the AI authoring discipline into the loop?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How do you make an agent-side discipline (the skill-writing method) mechanically enforced rather than advisory — so it cannot be silently skipped during foundation authoring?

## Content-presence routing check over foundations-workflow
**Path/Symbol:** `scripts/check.mjs` section 3d "Authoring routing gate" (:108–117); constant `WF = join(skillRoot, "pack-foundations", "foundations-workflow", "SKILL.md")`.
**Signature:** no function — conditional gate; reads one file and greps its body with `/writing-skills/.test(wt)`.
**Data Shape:** pass condition = the foundations-workflow skill text contains the substring `writing-skills` (i.e. it loads/routes to `pack-authoring/writing-skills`). The gate fires ONLY when `foundations-workflow/SKILL.md` exists — absence of the workflow itself is NOT a failure by design.

### Decisive source
```js
// ── 3d. Authoring routing gate: the skill-writing discipline must not be skipped ─
const WF = join(skillRoot, "pack-foundations", "foundations-workflow", "SKILL.md");
if (existsSync(WF)) {
  const wt = readFileSync(WF, "utf8");
  if (!/writing-skills/.test(wt)) {
    fail("foundations-workflow must route authoring through writing-skills (pack-authoring/writing-skills); add the load in Stage 4 editorial assembly");
  } else {
    ok("authoring routing: foundations-workflow loads writing-skills");
  }
}
```

**Flow:** (1) resolve the workflow skill inside the template's own pack tree; (2) if present, require its body to reference `writing-skills` — the load that pulls the authoring discipline into Stage 4 editorial assembly; (3) fail with an actionable message naming WHERE to add the load; otherwise print ok. Live run confirms: `[ok] authoring routing: foundations-workflow loads writing-skills`.
**Invariant:** the process skill may exist, but shipping it WITHOUT the authoring-discipline route is a hard template failure — content presence in a specific file is the proxy for "the workflow routes authoring through the discipline"; the gate deliberately stays silent when the workflow file is absent entirely (template subsets remain legal), trading strictness for composability.
**Probe:** live run at HEAD → `[ok] authoring routing: foundations-workflow loads writing-skills` inside exit-0 output; anchor `writing-skills` present in `pack-foundations/foundations-workflow/SKILL.md`. No direct test file exists (coverage caveat: the executable gate IS the probe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "check failures section skillFiles packs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: when your repo ships a process/method skill that agents must follow, add a cheap content-presence check tying it into the canonical gate — advisory-only disciplines rot. Adapt the watched file path and required-content token. Omit the existence-optional leniency if your target must always carry the workflow.
