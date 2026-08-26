<!-- capsule-v2 -->
# Profile patch layer — `cordis.patch.yml` + `dsh.profile.bundles`

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a DSH profile compose its runtime surface from bundle layers plus a top-level YAML-array patch layer (`cordis.patch.yml`), and how does `package.json` declare those bundles?

## DSH profile patch layer
**Path/Symbol:** `.dsh/profile/package.json` (whole file, 18 lines) — `dsh.profile.bundles` (8–16); `.dsh/profile/cordis.patch.yml` (whole file, 30 lines) — the top-level YAML-array loader patch entries (10–12), the `insert` example (28–30).
**Signature:** `package.json` declares `"dsh": { "profile": { "bundles": [ "@monotykamary/dsh-base", "@monotykamary/dsh-web-app", "dsh-fabric", "dsh-fovea" ] } }`; `cordis.patch.yml` is a top-level YAML array of loader patch entries (`id`-targeted `config` overrides, `disabled`, and `insert` lists; `!!js` expressions allowed).
**Data Shape:** the composed `cordis.yml` root stays an empty `[]` — the tree is built from the bundle patches in `dsh.profile.bundles` order, then this patch layer. Patch entries are `- id: <loader-id>` with `config` (override), `disabled: true`, or `insert` (list of entries to mount).

### Decisive source
```yaml
# cordis.patch.yml — a top-level YAML array of loader patch entries.
# The composed cordis.yml root stays an empty [] — the tree is built from the
# bundle patches in dsh.profile.bundles order, then this patch layer.
- id: tools
  config:
    maxParallelSubCalls: !!js Number.MAX_SAFE_INTEGER
# - id: command-goal
#   disabled: true
# - insert:
#     - id: project-prompts
#       name: '../../plugins/project-prompts/src/index.js'
```
```json
// package.json
{ "dsh": { "profile": { "bundles": ["@monotykamary/dsh-base", "@monotykamary/dsh-web-app", "dsh-fabric", "dsh-fovea"] } } }
```

**Flow:** (1) declare the bundle list in `package.json` `dsh.profile.bundles` (base + web-app + fabric + fovea); (2) the composed cordis config is built by applying each bundle's patch in order; (3) `cordis.patch.yml` is applied last as a top-level YAML array — each entry targets a loader `id` with a `config` override, `disabled: true`, or an `insert` list; (4) copy the three files into `$DSH_HOME/profiles/<name>/` and `pnpm install` there.

**Invariant:** the cordis root stays `[]` (the tree is built purely from ordered patches); patch entries are `id`-targeted; `!!js` expressions (e.g. `Number.MAX_SAFE_INTEGER`) are allowed in YAML; the patch layer is applied after every bundle layer.

**Probe:** no direct test file exists. Verified by direct source read (both files indexed `no_recorded_issue`, `freshness: not_tracked` — read source to confirm). `node scripts/check.mjs` verifies `dsh.profile.bundles` is nonempty and `cordis.patch.yml` exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "dsh.profile.bundles cordis.patch maxParallelSubCalls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bundle-list + top-level-YAML-array patch-layer composition model and the `id`-targeted override/disable/insert patch shape. Adapt the bundle names and the patch entries to the host. Omit the `dsh-fabric`/`dsh-fovea` bundles if those capabilities are not installed.
