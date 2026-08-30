<!-- capsule-v2 -->
# Serialized config env substitution & keyed merge — how do legacy JSON configs get env vars and layered merges without breaking comments?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you support `${ENV_VAR}`-style secrets in a JSONC config and merge remote/workspace overlays without clobbering user entries?

## Textual env replacement + identity-keyed overlay merge
**Path/Symbol:** `core/config/load.ts:resolveSerializedConfig` (lines 74–96), `configMergeKeys` (98–110), `loadSerializedConfig` (112–167).
**Signature:** `resolveSerializedConfig(filepath: string): SerializedContinueConfig`.
**Data Shape:** config declares `env: string[]` naming variables; overlays are remote config URL + per-workspace `.continuerc` files with `mergeBehavior`.

### Decisive source
```ts
let content = fs.readFileSync(filepath, "utf8");
const config = JSONC.parse(content);            // parse ONCE to read the declared env list
if (config.env && Array.isArray(config.env)) {
  const env = { ...process.env, ...getContinueDotEnv() };
  config.env.forEach((envVar) => {
    if (envVar in env) {
      content = (content as any).replaceAll(new RegExp(`"${envVar}"`, "g"), `"${env[envVar]}"`);
      // substitute IN THE RAW TEXT — comments survive, values stay quoted strings
    }
  });
}
return JSONC.parse(content) as unknown as SerializedContinueConfig;   // parse AGAIN
// identity keys decide what an overlay may touch:
const configMergeKeys = {
  models: (a, b) => a.title === b.title,
  contextProviders: (a, b) => {
    if (a.name !== "http" || b.name !== "http") return a.name === b.name;
    return a.name === b.name && a.params?.url === b.params?.url; // two http providers differ by URL
  },
  slashCommands: (a, b) => a.name === b.name,
  customCommands: (a, b) => a.name === b.name,
};
// order: base -> remote (try/catch warn) -> workspace .continuerc files with their own mergeBehavior
if (os.platform() === "linux" && !isSupportedLanceDbCpuTargetForLinux(ide)) {
  config.disableIndexing = true;                 // platform sanity switch after merges
}
```

**Flow:** parse → collect declared env names → regex-substitute quoted occurrences in raw text → re-parse → validate → optional remote merge → workspace merges by identity keys → platform-specific capability switches.
**Invariant:** only *quoted exact-name* strings are substituted (no expression language, no recursion), and overlays can only update entries they can *identify* via the key functions — a remote config cannot silently duplicate your models because it spells the title differently.
**Probe:** no direct suite for `loadSerializedConfig` at this pin (coverage caveat — runner not installed; see work record). The observable contract to test once installed: a config.json containing `"env": ["OPENAI_API_KEY"]` and `"apiKey": "OPENAI_API_KEY"` parses with the value injected while `// comment` lines remain.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "resolveSerializedConfig env", limit: 8 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.load.intermediateToFinalConfig", direction: "inbound", depth: 2 });
// loadContinueConfigFromJson is the sole production caller of this plane; doLoadConfig reaches it on JSON fallback
```

## Verdict
Adopt double-parse textual substitution for JSONC-with-env and identity-keyed overlay merging; adapt the identity keys to your entity names; omit the Linux LanceDB CPU-target switch unless you ship local vector indexes.
