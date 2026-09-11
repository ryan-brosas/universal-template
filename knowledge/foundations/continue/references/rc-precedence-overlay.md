<!-- capsule-v2 -->
# Workspace rc overlay precedence — how do repo-local .continuerc files merge over a user config without clobbering it?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you collect per-workspace override files and merge them with per-file aggressiveness while staying fail-open?

## Fail-open collection + per-file mergeBehavior ladder
**Path/Symbol:** `core/config/json/loadRcConfigs.ts:getWorkspaceRcConfigs` (5–31); merge ladder in `core/config/load.ts:loadSerializedConfig` (112–167); merge kernel `core/util/merge.ts:mergeJson` (5–59); direct suite `core/util/merge.test.ts`.
**Signature:** `getWorkspaceRcConfigs(ide: IDE): Promise<ContinueRcJson[]>` ; `mergeJson(first, second, mergeBehavior?: ConfigMergeType, mergeKeys?): any`.
**Data Shape:** each rc declares its own `mergeBehavior`; identity functions exist only for `models` (title), `contextProviders` (name, +url for http), `slashCommands`/`customCommands` (name).

### Decisive source
```ts
// collection: regular files OR symlinks named *.continuerc.json, per workspace dir; fail-open []
const ls = await ide.listDir(dir);
const rcFiles = ls.filter((e) => (e[1] === 1 || e[1] === 64) && e[0].endsWith(".continuerc.json"))
  .map((entry) => joinPathsToUri(dir, entry[0]));
// ... JSONC.parse each read; catch -> console.debug + return []

// ladder: base -> remote overlay ("merge") -> EACH workspace rc with ITS OWN mergeBehavior
config = mergeJson(config, remoteConfigJson, "merge", configMergeKeys);
for (const workspaceConfig of workspaceConfigs) {
  config = mergeJson(config, workspaceConfig, workspaceConfig.mergeBehavior, configMergeKeys);
}

// kernel: deep clone first (JSON roundtrip drops functions!), arrays identity-keyed:
const keptFromFirst: any[] = [];
firstValue.forEach((item) => { if (!secondValue.some((i2) => mergeKeys[key](item, i2))) keptFromFirst.push(item); });
copyOfFirst[key] = [...keptFromFirst, ...secondValue];   // second WINS collisions AND sorts after
// objects recurse WITHOUT mergeKeys; scalars second-wins; throw -> fail-open {...first, ...second}
```

**Flow:** list workspace dirs → collect+parse `.continuerc.json` (any failure → empty list) → validate base config (fatal gate upstream) → optional remote merge → sequential per-rc merges in workspace order → platform capability switches (`disableIndexing` on unsupported Linux LanceDB targets).
**Invariant:** collection and merging are independently fail-open/fail-soft (kernel catches and shallow-spreads); an overlay can only REPLACE identified entries (identity keys), everything else appends — so a typo'd title in an rc ADDS a model instead of deleting yours; recursion drops `mergeKeys`, so identity resolution is top-level-per-key only.
**Probe:** `core/util/merge.test.ts` (11 cases, read in full) pins concat vs overwrite vs identity-keyed replace (`id:2 updated` replaces in place while keeping position among kept-first items), null/undefined passthrough, and the function-value error path returning `{...first, ...second}`. Runner block recorded (vitest not installed); suite text verified byte-level this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "getWorkspaceRcConfigs mergeJson mergeBehavior", limit: 8 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.util.merge.mergeJson", direction: "inbound", depth: 2 });
// observed inbound: loadSerializedConfig (remote + rc overlays); sibling kernel mergePackages lives in packages/config-yaml
```

## Verdict
Adopt per-file mergeBehavior with identity-keyed array merges and fail-open collection for layered config systems; adapt identity keys to your entities and decide explicitly whether nested objects need their own identities (upstream does NOT recurse keys); omit the remote-server rung if you have no managed config service. Boundary note: env substitution + key definitions themselves live in serialized-config-env-merge.md — this capsule owns collection, ordering, and the merge kernel.
