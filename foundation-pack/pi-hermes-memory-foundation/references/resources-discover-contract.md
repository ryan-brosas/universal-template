<!-- capsule-v2 -->
# Host resource discovery — how does an extension contribute its own skill directories to a host that only auto-discovers its own skill root, without losing project scoping?

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** When a host loads skills from fixed roots it owns, how does an extension register additional generated-skill directories — and keep them separated from user-installed skills — while still resolving per-project skill dirs?

## Discovery callback doubles as the skill-store rebind point
**Path/Symbol:** `src/index.ts:resolveProjectSkillDiscovery` (:62–77), `registerProjectSkillDiscoveryHandler` (:79–87), wiring `pi.on("resources_discover", …)` (:220); `src/project.ts:detectProjectSkills` (:151–157); `SkillStore.setProjectContext` (:196–199), `getGlobalSkillsDir` (:175–177), `ensureDiscoveredRoots` (:201–206).
**Signature:** `resolveProjectSkillDiscovery(skillStore: SkillStore, projectsMemoryDir: string | undefined, cwd?: string): { skillPaths: string[] }`.
**Data Shape:** host event carries `{ cwd?: string }`; return value is `{ skillPaths: string[] }` — always `[globalSkillsDir]`, plus the project skills dir when cwd resolves to a project. SIDE EFFECT: `skillStore.setProjectContext(detected.name, detected.skillsDir)` mutates store state on every discovery call; there is no separate rebind event.

### Decisive source
```ts
// src/index.ts:67-76
const detected = detectProjectSkills(projectsMemoryDir, cwd);
skillStore.setProjectContext(detected.name, detected.skillsDir);

// Pi auto-discovers its own `~/.pi/agent/skills/`, but this extension keeps
// its generated skills in a directory of its own so users can audit, wipe, or
// ignore them without touching skills they installed themselves (#126). Both
// of ours must therefore be contributed here.
const skillPaths = [skillStore.getGlobalSkillsDir()];
if (detected.skillsDir) skillPaths.push(detected.skillsDir);
return { skillPaths };
```

**Flow:** (1) host fires `resources_discover` with the active cwd; (2) `detectProjectSkills` reuses the git-walk project detector (`detectProject`) and derives `skillsDir = memoryDir/skills` (null outside a project); (3) the resolved name/dir are pushed INTO the SkillStore before answering; (4) the reply contributes `[extension-global-root, project-root?]` — the extension's global root rides EVERY answer so host-side loading never depends on session state. At session start the root also calls `refreshSkillProjectContext(ctx.cwd)` (:131–138) and `ensureDiscoveredRoots()` (:201–206 mkdir -p both roots) so the first load finds existing dirs.
**Invariant:** the extension-owned global skills dir is contributed unconditionally, even with no project — separation of generated vs user-installed skills (#126) must not degrade to "project skills only"; and because discovery mutates the SkillStore, every code path that can change cwd must funnel through this one resolver rather than patching store fields ad hoc.
**Probe:** `tests/handlers/resources-discover.test.ts` — registers `resources_discover` and returns both paths for `/tmp/demo-repo`; asserts `store.getProjectName() === "demo-repo"` + `getProjectSkillsDir()` after resolution; homedir cwd yields global-only paths AND nulled project context. Executed GREEN pre-write: 3 passed / 0 failed (`npx tsx --test`). Coverage: all cited source+test paths `no_recorded_issue` @ gen 2026-08-24T14:05:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "resolveProjectSkillDiscovery resources_discover skillPaths setProjectContext", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the contract shape: a host queryable that returns extra skill roots AND is the single mutation point for per-project skill context. Adapt the event name (`resources_discover`), the cwd plumbing, and where the extension-global root lives to your host. Omit `ensureDiscoveredRoots` if the host guarantees directory creation. Caveat: `detectProjectSkills` inherits `detectProject`'s git-worktree identity rules — see project-identity-resolution.md before porting the detector itself.
