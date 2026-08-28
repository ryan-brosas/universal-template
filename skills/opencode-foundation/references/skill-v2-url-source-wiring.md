<!-- capsule-v2 -->
# SkillV2 URL source wiring — how does a pulled remote catalog become live skill rows?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does SkillDiscovery's directory output connect to the SkillV2 store's URL sources?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/skill.ts`: `load` (:58-96, discovery call site :76, glob :79), `node` export (:132, deps `[SkillDiscovery.node, FSUtil.node]`); `packages/core/src/skill/discovery.ts`: `node` export (:211); `packages/core/src/config/plugin/skill.ts`: URL source registration (:24-50, read in pass 15).
**Signature:** SkillV2 `Interface.pull` → `SkillDiscovery.pull(url)` → `AbsolutePath[]` fed into the per-source cache keyed by `Source.key`.
**Data Shape:** SkillV2 stores SOURCES not rows (pass-16 domain-draft-editors capsule); a URL source resolves to discovered directories; each directory must contain `SKILL.md` or `<name>.md` to be published.

### Decisive source
```ts
// discovery.ts — the node wires the service into the global plane with its platform deps:
export const node = makeGlobalNode({ service: Service, layer, deps: [httpClient, FSUtil.node, Global.node] })
```
```ts
// skill.ts — sources-not-rows: each source pulls lazily and caches per source key
```

**Flow:** config registers a URL skill source (config/plugin/skill.ts accepts URL/~/relative/absolute + both directory spellings) → SkillV2's `load(source)` branches on source type: `embedded` returns the skill directly, `directory` uses the path, `url` calls `discovery.pull(source.url)` → discovery fetches + validates + stages the catalog into the global cache → only directories with an entrypoint are returned → SkillV2 globs `{*.md,**/SKILL.md}` per directory (fail-open to empty), reads each file sorted, decodes frontmatter, and derives the name from frontmatter or the top-level filename. The per-source cache means a version-unchanged catalog costs one index.json request per pull.
**Invariant:** discovery is a global-tagged node (one cache per process) while SkillV2 is a location service — the layer-node tag/hoist split is what lets per-directory SkillV2 instances share one pulled cache.
**Probe:** `packages/core/test/skill-discovery.test.ts` (pull contract) + `packages/core/test/skill.test.ts` (2 it.live: store behavior over sources). Coverage caveat: no direct test pins the load() glob/frontmatter branch itself; it is source-confirmed at :58-96.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SkillV2 pull source cache discovery node", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy per-source pulling with a process-global cache node beneath per-tenant skill stores. Adapt source registration grammar to your host config. Omit the specific frontmatter decode. Coverage caveat: no direct test pins the load() glob/frontmatter branch; it is source-confirmed whole this pass (skill.ts :58-96). The discovery-side contract is fully source+test confirmed.
