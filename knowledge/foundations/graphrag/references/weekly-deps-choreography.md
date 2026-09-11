<!-- capsule-v2 -->
# Weekly automation choreography — how do the two dependency cron workflows pair into one scheduled agent-driven maintenance window?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How are the two Bun-run TypeScript scripts wired into GitHub Actions so the weekly schedule both suppresses Dependabot and dispatches exactly one Copilot-agent sweep?

## Key facts
**Path/Symbol:** `.github/workflows/update-deps.yml` (schedule :4-5, bun setup :17-20, run step :22-25) and `.github/workflows/close-dependabot-prs.yml` (identical skeleton).
**Signature:** both: `on: schedule: cron "0 0 * * 1"` + `workflow_dispatch`; `permissions: contents: read` only; single `readme` job on ubuntu-latest.
**Data Shape:** runtime contract = oven-sh/setup-bun@v2 pinned `bun-version: 1.3.14`; secret `GH_APP_ACCESS_TOKEN` injected as env for the script process; scripts execute top-level-await module code via `bun run ./scripts/*.ts` — no build step, no node_modules, no compile.

### Decisive source
```yaml
# .github/workflows/update-deps.yml :8-25 — minimal-permission single-step dispatch:
permissions:
  contents: read
jobs:
  readme:
    steps:
      - name: Setup Bun
        uses: oven-sh/setup-bun@v2
        with:
          bun-version: 1.3.14
      - name: Create Update Dependencies Sweep Issue
        env:
          GH_APP_ACCESS_TOKEN: ${{ secrets.GH_APP_ACCESS_TOKEN }}
        run: bun run ./scripts/open-deps-update-issue.ts
```

**Flow:** every Monday 00:00 UTC BOTH workflows fire in the same window → close-dependabot-prs.ts closes all open `dependabot[bot]` PRs → open-deps-update-issue.ts opens ONE agent-assigned sweep issue whose custom_instructions point at the repo-owned update-deps skill → Copilot coding agent works the issue on `main` and opens a PR carrying the sweep + a semversioner changelog entry (enforced by the skill's completion checklist).
**Invariant:** least privilege — `contents: read` suffices because ALL GitHub mutations happen through the REST API with the PAT (`GH_APP_ACCESS_TOKEN`), never through the workflow's own GITHUB_TOKEN; both jobs share one runtime pin so the two scripts can never drift apart on Bun version; the pairing is semantic — closing old bot PRs and opening the new agent issue is ONE maintenance transaction, split across two workflows only for independent failure.
**Probe:** `grep -n 'cron:' .github/workflows/update-deps.yml .github/workflows/close-dependabot-prs.yml` = `:5` in each, identical `"0 0 * * 1"`; `grep -c 'GH_APP_ACCESS_TOKEN' scripts/open-deps-update-issue.ts scripts/close-dependabot-prs.ts` = 2 per file.

## Get live surrounding code
**Retrieve:** workflow YAML nodes resolve via search_code:
```
codebase-memory-mcp cli search_code '{"project":"graphrag","pattern":"bun-version"}'
```
rank#1-2 = `.github/workflows/close-dependabot-prs.jobs` + `.github/workflows/update-deps.jobs` :11-26 line-exact.

## Verdict
Adopt the paired-cron choreography (suppress old bot output + dispatch one skill-pointing agent issue) and the PAT-over-GITHUB_TOKEN least-privilege shape; adapt cron slot, secret name, and Bun pin to host; omit the hardcoded repo constants. Coverage: `no_recorded_issue`; smoke-only surface (workflow runs are the direct test).
