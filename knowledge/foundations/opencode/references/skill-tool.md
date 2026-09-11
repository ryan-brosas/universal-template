<!-- capsule-v2 -->
# Skill tool — load a named skill's instructions

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a coding agent load a skill by name so the model follows its instructions?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/skill.ts` (70 lines): `Parameters` (:8-10), `SkillTool` (:12), `execute` (:15+).
**Signature:** `execute({name}, ctx)` — `Skill.Service` lookup by name from `available_skills`, returns the skill's instructions.
**Data Shape:** `Parameters = {name: string}` (the skill name from `available_skills`); output = the skill's instruction content.

### Decisive source
```ts
export const Parameters = Schema.Struct({
  name: Schema.String.annotate({ description: "The name of the skill from available_skills" }),
})
// SkillTool.execute resolves the Skill.Service and returns the skill's instructions
```

**Flow:** the model calls `skill` with a skill name; the tool looks it up from the available-skills registry and returns its instructions so the model can follow them.
**Invariant:** skill names must come from `available_skills` (unknown names fail instructively).
**Probe:** `packages/opencode/test/tool/skill.test.ts` (known skill returns instructions; unknown skill errors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SkillTool skill available_skills instructions load", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the the name-based skill-loading tool (return a named skill's instructions); adapt the skill registry and instruction format to host.
