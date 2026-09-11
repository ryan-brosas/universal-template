<!-- capsule-v2 -->
# Profile install choreography — copy patch layer → `pnpm install` → `dsh --profile`

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How is a DSH profile installed and activated from the template's shipped patch layer — the exact copy/install/activate choreography — and in what order are plugin bundles resolved?

## Profile install + bundle resolution order
**Path/Symbol:** `.dsh/profile/README.md:7-17` (Install section), `:20-30` (What the files do), `:32-37` (Notes); `.dsh/profile/package.json:8-16` (`dsh.profile.bundles`). Graph: `search_code --pattern 'dsh.profile.bundles'` resolves `.dsh/profile/README.md` Module (lines 1-38).
**Signature:** shell choreography — `cp package.json cordis.patch.yml pnpm-workspace.yaml ~/.dsh/profiles/web/` → `cd ~/.dsh/profiles/web && pnpm install` → `dsh --profile web`. Profiles live at `$DSH_HOME/profiles/<name>/` (default `~/.dsh/profiles/`); the `web` profile auto-initializes on first use from shipped templates.
**Data Shape:** exactly three files compose the profile: `package.json` (manifest declaring the ordered `dsh.profile.bundles` list), `cordis.patch.yml` (the user's own top-level YAML-array patch layer, applied after every bundle layer), `pnpm-workspace.yaml` (workspace settings: `packages: [- .]`, `nodeLinker: hoisted`, `autoInstallPeers: false`).

### Decisive source
```markdown
# 1. Copy the three files into your profile directory
cp package.json cordis.patch.yml pnpm-workspace.yaml ~/.dsh/profiles/web/

# 2. Install the out-of-tree plugins (dsh-fabric, dsh-fovea) into the profile
cd ~/.dsh/profiles/web && pnpm install

# 3. Restart / load the profile
dsh --profile web

- **`package.json`** — ... `dsh.profile.bundles` is an ordered list of plugin
  bundles resolved from the dsh installation first
  (`@monotykamary/dsh-base`, `@monotykamary/dsh-web-app`), then from the
  profile's own `node_modules` (`dsh-fabric`, `dsh-fovea`).
```

**Flow:** (1) copy the three profile files into `$DSH_HOME/profiles/<name>/`; (2) run `pnpm install` inside that directory so out-of-tree plugins (`dsh-fabric`, `dsh-fovea`) land in the *profile's own* `node_modules`; (3) activate with `dsh --profile <name>`; (4) at composition, each bundle in `dsh.profile.bundles` order contributes its patch — resolved from the dsh installation **first**, falling back to the profile's `node_modules`.

**Invariant:** bundle resolution order is installation-first, profile-local second (an out-of-tree plugin MUST be `pnpm install`ed into the profile dir or its bundle silently won't resolve); always edit `cordis.patch.yml`, never the composed `cordis.yml` (its composed root stays an empty `[]`); MCP servers are configured in `$DSH_HOME/mcp.yaml`, NOT in cordis; custom agent presets live in `$DSH_HOME/.agent-presets/<id>/`.

**Probe:** no direct test file exists. Deterministic probes executed at HEAD: `grep -c 'resolved from the dsh installation first' .dsh/profile/README.md` → 1; `node scripts/check.mjs` §4 verifies `dsh.profile.bundles` is a nonempty array and `cordis.patch.yml` exists (see `canonical-check.md`). Coverage caveat: README is prose doctrine — the loader itself lives in the DSH harness, not this template.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "dsh.profile.bundles", limit: 10, fields: ["signature", "name", "file"] });
// doc-shaped graph fallback:
// codebase-memory-mcp cli search_code --project dsh-template --pattern 'dsh.profile.bundles'
```

## Verdict
Adopt the three-file profile shape and the copy → profile-local `pnpm install` → `dsh --profile` activation choreography with installation-first bundle resolution. Adapt the bundle names (`@monotykamary/*`, `dsh-fabric`, `dsh-fovea`) and profile name (`web`) to the host. Omit the auto-init-on-first-use behavior unless the host harness implements it.
