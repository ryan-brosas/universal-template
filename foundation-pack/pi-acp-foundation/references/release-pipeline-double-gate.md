<!-- capsule-v2 -->
# Release pipeline double gate — how do you run two entry points (manual dispatch + tag push) to one publish surface without double-publishing?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A package can be released two ways — a manual `workflow_dispatch` that bumps the version and cuts the tag, and an automatic tag-push pipeline — both ending in `npm publish`. How do you keep the two paths from racing each other or publishing a version twice, and which guards belong in which workflow?

## Two workflows, one publish surface, guards mirrored so either path is safe alone
**Path/Symbol:** `.github/workflows/release.yml` (whole, 68L) — version-input regex :30-34, already-published guard :36-41, gates-before-commit :43-47, commit+tag+push :49-57, provenance publish :59-60, gh release :62-68. `.github/workflows/npm-publish.yml` (whole, 53L) — tag-trigger :9-10, tag↔package.json agreement :21-29, already-published guard :31-37, publish :45-46.
**Signature:** `workflow_dispatch` with `inputs.version: string` (release.yml) vs `on: {workflow_dispatch, push: {tags: ['v*']}}` (npm-publish.yml). Both require `permissions: {contents: write, id-token: write}` — the latter for npm OIDC provenance.
**Data Shape:** version grammar pinned in BOTH workflows: `^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$` (release.yml greps the input; npm-publish.yml derives `TAG_VERSION="${GITHUB_REF_NAME#v}"` and compares against `package.json`). The double-publish guard is the same probe in both: `npm view pi-acp-jetbrain@<version> version >/dev/null 2>&1` → exit 1 if it resolves.

### Decisive source
```yaml
# release.yml :36-41 — the idempotence guard BEFORE any build or commit
- name: Ensure version not already published
  run: |
    if npm view pi-acp-jetbrain@${{ github.event.inputs.version }} version >/dev/null 2>&1; then
      echo "pi-acp-jetbrain@${{ github.event.inputs.version }} is already on npm"
      exit 1
    fi
```

**Flow:** release.yml (the primary path): validate input grammar → already-published guard → `npm ci` → `npm version <v> --no-git-tag-version` (bumps package.json + lock) → typecheck + lint + test + build → commit ONLY the two manifest files as `chore(release): <v>` → tag `v<v>` → push HEAD:main and the tag → `npm publish --provenance` → `gh release create --generate-notes`. npm-publish.yml (the tag-push path): if triggered by a tag, verify tag version == package.json version → already-published guard → `npm ci` → `build --if-present` → test → publish. The two paths share the guard, so whichever fires second (e.g. the tag push from release.yml re-triggering npm-publish.yml) exits 1 harmlessly at the guard.
**Invariant:** no path publishes without (a) the version grammar holding, (b) the version not already on npm, and (c) release.yml additionally running the full gate suite BEFORE the version commit — a failing gate never produces a tag. The version commit touches exactly `package.json` + `package-lock.json` (no dist in git).
**Probe:** no direct test exists for workflow YAML at this pin (recorded caveat); the grammar and guard logic are pinned by the workflow files themselves and the release history (`chore(release): 0.0.40` at HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "release workflow npm publish provenance tag version guard", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mirrored already-published guard in BOTH paths (idempotence lives at the publish surface, not in one workflow), the grammar check on every entry point, and gates-before-version-commit ordering. Adapt the package name probe and version grammar to your registry. Omit the OIDC provenance flag only if your registry lacks it — but then the `id-token` permission is dead weight. No direct test coverage for workflow YAML at this pin.
