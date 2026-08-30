<!-- capsule-v2 -->
# Pi-shadowing write refusal — never create a global skill the host silently shadows

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** When your extension writes into a directory namespace a HOST also loads (with its own precedence rules), how do you prevent writes that succeed on disk but change nothing about agent behavior?

## Shadow refusal
**Path/Symbol:** `src/store/skill-store.ts` — `findShadowingPiGlobalSkill` (:336–340), its docstring :323–335 (the #125 contract), `create` shadow arm :423–434; constructor dir split :166–167 (`globalSkillsDir` = `<agentRoot>/pi-hermes-memory/skills`, `piGlobalSkillsDir` = `<agentRoot>/skills`); direct tests `tests/store/skill-store.test.ts:621–659`.
**Signature:** `findShadowingPiGlobalSkill(slug: string): Promise<string | null>`.
**Data Shape:** returns the shadowing path (Pi's own `<piGlobalSkillsDir>/<slug>/SKILL.md`) when it exists, else null. The two roots differ only by the extension subdirectory.

### Decisive source
```ts
// findShadowingPiGlobalSkill docstring (323-335) states the invariant:
// "Pi keys skills by name, first-loaded wins, and ~/.pi/agent/skills/ is
//  auto-discovered at higher precedence than anything an extension contributes
//  via resources_discover. A global skill we write under a name that also
//  exists there is never the copy Pi loads — silent write-loss (#125)."
// "Callers refuse the write and name both paths instead, which makes the
//  shadowed state impossible to create rather than merely reported after the fact."

private async findShadowingPiGlobalSkill(slug: string): Promise<string | null> {
  if (path.resolve(this.piGlobalSkillsDir) === path.resolve(this.globalSkillsDir)) return null;
  const candidate = path.join(this.piGlobalSkillsDir, slug, "SKILL.md");
  return await exists(candidate) ? candidate : null;
}

// create() arm (:423-434) — runs AFTER duplicate/similar/name-collision, global scope only:
const shadowedBy = await this.findShadowingPiGlobalSkill(slug);
if (shadowedBy) return {
  success: false,
  error: `Pi already loads a global skill named '${slug}' from ${shadowedBy}. `
    + `Pi keys skills by name and loads its own root first, so a skill written to `
    + `${path.join(this.globalSkillsDir, slug, "SKILL.md")} would never be the copy in effect. `
    + `Choose a different name, or edit ${shadowedBy} directly.`,
  conflictType: "name-collision", suggestedAction: "rename",
};
```

**Flow:** (1) The store keeps TWO separate global roots: where it writes (`pi-hermes-memory/skills`) and where the host loads first (`skills`). (2) Before any global-scope create, it checks whether the host already owns that slug. (3) If yes, the write is REFUSED with an error naming both paths and explaining the load-precedence mechanics — the model can self-correct by renaming or editing the host file. (4) Project-scoped skills are exempt: a project skill reusing a Pi-global name is legal because project discovery shadows differently (direct test `still allows a project skill to reuse a name taken in Pi's global root` :647).

**Invariant:** the failure mode is prevented STRUCTURALLY, not detected after the fact — there is no code path that writes a shadowed copy. The same-root guard (`resolve(a)===resolve(b)` → null) makes misconfiguration degrade to "no shadow check" instead of blocking all writes. Note this differs from the sibling near-name collision gate: similarity gates protect against semantic duplicates inside the extension's OWN store, while the shadow gate protects against cross-root precedence loss; they run in sequence (duplicate → similar → name-collision → shadow) and produce different `suggestedAction` values.

**Probe:** `tests/store/skill-store.test.ts` — `writes global skills to the extension directory, never Pi's root` (:622), `refuses a global name Pi already loads instead of writing a shadowed copy` (:631), `still allows a project skill to reuse a name taken in Pi's global root` (:647). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "findShadowingPiGlobalSkill shadowed silent write-loss", limit: 5 });
// live-verified rank-1: SkillStore.findShadowingPiGlobalSkill :336-340
```

## Verdict
Adopt the pattern whenever a plugin writes into a namespace the host also indexes: keep the plugin's output root distinct from any host-owned root, refuse (don't warn-after) writes whose names the host would shadow at higher precedence, and put the load-precedence explanation INTO the error so the caller can fix it in one turn. Adapt root names and slug rules. Omit if your target has exactly one skill authority.
