<!-- capsule-v2 -->
# Plugin manager lifecycle — how do 19 built-in plugins get registered, env-activated, and resolved to live adapters with Local fallback?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the resolution order for a storage adapter when nothing is configured, and why does emailAdapter return null where storage returns Local?

## Category-scoped adapter resolution
**Path/Symbol:** `packages/nocodb/src/helpers/NcPluginMgrv2.ts:NcPluginMgrv2` (whole 338L; defaultPlugins registry :37–58).
**Signature:** `static init(ncMeta?)`, `private static initPluginsFromEnv()`, `static async storageAdapter(ncMeta?): Promise<IStorageAdapterV2>`, `static async emailAdapter(isUserInvite = true, ncMeta?)`, `static async webhookNotificationAdapters(title, ncMeta?)`, `static async test(args)`.
**Data Shape:** nc_plugins rows {id,title,version,logo,icon,description,tags,category,input_schema} + active flag + input JSON; init() throws on DUPLICATE plugin ids at boot.

### Decisive source
```ts
const pluginData = await ncMeta.metaGet2(RootScopes.ROOT, RootScopes.ROOT, MetaTable.PLUGIN,
  { category: PluginCategory.STORAGE, active: true });

if (!pluginData) return new Local();
...
public static async emailAdapter(isUserInvite = true, ...) {
  ...
  if (!pluginData) {
    // return null to show the invite link in UI
    if (isUserInvite) return null;
    // for webhooks, throw the error
    throw new Error('Plugin not configured / active');
  }
```
(:191–:201, :231–:236)

**Flow:** init() seeds every defaultPlugins row (insert-if-missing; update metadata on version change), validates id uniqueness up-front, then applies ENV activations: NC_S3_BUCKET_NAME+region/endpoint activates S3 (credentials optional — IAM roles work), NC_SMTP_FROM/HOST/PORT activates SMTP → adapters resolve lazily per use: metaGet2 by category+active → find the config class by TITLE → `new builder(ncMeta, pluginData)` → JSON.parse input → plugin.init(input) → getAdapter(). emailAdapter's null-vs-throw split lets user invites degrade to a shown link while webhooks must fail loudly.
**Invariant:** the DB row is the source of truth for ACTIVE config; the in-code config class only supplies builder/schema. Env activation OVERWRITES stored input each boot — operator env wins over UI-saved settings. Storage falls back to LOCAL disk so a fresh install can upload files with zero configuration. test() builds a THROWAWAY plugin instance from submitted input (never persisting) so users can validate credentials safely.
**Probe:** `cd packages/nocodb && grep -c "duplicateIds" src/helpers/NcPluginMgrv2.ts` (=3: decl+check+message) and `grep -c "initPluginsFromEnv" src/helpers/NcPluginMgrv2.ts` (=2: def + call) and `grep -c "new Local()" src/helpers/NcPluginMgrv2.ts` (=1) and `grep -c "isUserInvite" src/helpers/NcPluginMgrv2.ts` (=2: param + check).
**Direct test:** none upstream for NcPluginMgrv2.ts — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NcPluginMgrv2 storageAdapter emailAdapter initPluginsFromEnv", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt DB-row-as-truth + env override + category-scoped lazy resolution + Local/null fallbacks; adapt the plugin set and schema; omit if your platform has a native extension host. Coverage caveat: grep-pinned only.
