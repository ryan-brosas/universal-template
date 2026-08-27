<!-- capsule-v2 -->
# Release provenance gate — how should a small TS package gate npm releases on tag↔version parity and ship provenance without long-lived tokens?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How should a small TS package gate npm releases on tag↔version parity and ship provenance without long-lived tokens?

## Keyless OIDC publish workflow with fail-fast parity check
**Path/Symbol:** `.github/workflows/publish.yml` (whole file, `:1-39`).
**Signature:** Not a callable; a GitHub Actions workflow document.
**Data Shape:** Trigger `push: tags: ['v*']`; permissions `contents: read` + `id-token: write` ONLY (no `NPM_TOKEN` secret exists anywhere in the file); concurrency group `npm-publish` with `cancel-in-progress: false`; job steps: checkout → bash parity check → pnpm/action-setup → setup-node (node 24, `registry-url: https://registry.npmjs.org/`) → frozen-lockfile install → `pnpm run check` → plain `npm publish`.

### Decisive source
```yaml
# .github/workflows/publish.yml :8-14 and :21-28 + :37-39
permissions:
  contents: read
  id-token: write

concurrency:
  group: npm-publish
  cancel-in-progress: false

      - name: Verify tag matches package version
        shell: bash
        run: |
          version="$(node -p "require('./package.json').version")"
          if [[ "$GITHUB_REF_NAME" != "v$version" ]]; then
            echo "Tag $GITHUB_REF_NAME does not match package version $version" >&2
            exit 1
          fi
      - run: pnpm --config.minimum-release-age=0 install --frozen-lockfile
      - run: pnpm run check
      - run: npm publish
```

**Flow:** v* tag push → serialized under the `npm-publish` concurrency group (a second tag can never interleave a half-published state) → tag↔package.json parity exits 1 BEFORE any dependency install exists to be polluted → frozen-lockfile install (`minimum-release-age=0` so brand-new dep releases are acceptable) → repo quality gate → `npm publish`, authenticated by the workflow's OIDC id-token (npm trusted publishing), producing registry provenance with zero stored credentials.
**Invariant:** The parity gate must run before install (fail-fast, no partial dependency state); releases must serialize; provenance must come from short-lived OIDC identity, never a long-lived token in repo secrets.
**Probe:** Content-level verification only — this is a CI-only artifact no repository test executes; every structural claim above was read directly from the pinned file this pass (honest caveat carried forward).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", label: "File", qn_pattern: "publish", limit: 10 });
// observed live: total 1 — dsh-codex..github.workflows.publish.yml File node, has_more=false
```

## Verdict
Adopt tag↔version parity-before-install, serialized release concurrency, permissions minimalism (`contents:read` + `id-token:write` only), and keyless `npm publish`. Adapt runner/action versions and the package manager invocation to the host repo. Omit this repo's specific node/pnpm version pins. Coverage caveat: check_index_coverage clean for the workflow path; CI-only evidence class recorded above.
