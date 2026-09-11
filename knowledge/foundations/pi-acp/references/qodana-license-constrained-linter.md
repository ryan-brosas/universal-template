<!-- capsule-v2 -->
# Qodana license-constrained linter — what do you do when your static-analysis gate cannot analyze your language?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo's CI static-analysis gate (Qodana) is licensed at Community tier, but the repo's language (TypeScript) needs an Ultimate-tier linter. Do you fail the gate, drop it, or run a mismatched linter — and where does the real language baseline move?

## Keep the gate green with a deliberately mismatched linter; document the real baseline in-file
**Path/Symbol:** `qodana.yaml` (whole, 57L) — profile :13-14, commented failureConditions :40-49, decisive license comment :51-56, `linter: qodana-jvm-community` :57. `.github/workflows/qodana_code_quality.yml` (whole, 39L) — trigger matrix :10-15, checkout with PR head ref :23-26, qodana-action step :28-39 (`pr-mode: false`, `use-caches: true`, `post-pr-comment: true`, `use-annotations: true`, `upload-result: false`, `push-fixes: 'none'`).
**Signature:** `linter: qodana-jvm-community` — the ONLY non-comment setting besides `version: '1.0'` and `profile.name: qodana.starter`. No failureConditions are enabled (all commented out).
**Data Shape:** the workflow grants `permissions: {contents: write, pull-requests: write, checks: write}` for PR comments and check annotations; the action is pinned (`JetBrains/qodana-action@v2026.2`) with `QODANA_TOKEN` from secrets.

### Decisive source
```yaml
# qodana.yaml :51-57 — the license constraint is documented IN the config, next to the setting it explains
# The pi-acp Qodana Cloud org is on the Community license. The JetBrains linter/license
# matrix (pricing.html#pricing-linters-licenses) marks JavaScript and TypeScript as
# Ultimate/Ultimate Plus only; Community covers JVM, Android, Python, .NET, and C/C++.
# qodana-js therefore cannot run here (it fails with "Community license that doesn't support
# Qodana for JS"). Keep a Community linter so the gate stays green; it is NOT a TS scan.
# The real TypeScript baseline is the per-turn IntelliJ inspection (ide_idea_lint_files)
# plus local lint/typecheck in check.yml. Enabling qodana-js needs a Qodana Ultimate license.
linter: qodana-jvm-community
```

**Flow:** PR/push/main → qodana_code_quality.yml → checkout (PR head sha, depth 1) → qodana-action runs the JVM Community linter over the tree → results posted as PR comment + check annotations. The gate is green by construction (a JVM linter finds nothing actionable in a TS repo) — its VALUE is the pipeline being proven end-to-end (token, caching, annotations) so that upgrading the license is a one-line `linter:` change, not a CI rebuild. The REAL TypeScript quality baseline lives in two other planes: the per-turn IntelliJ inspection gate (`ide_idea_lint_files`, owned by post-turn-inspection-gate.md) and `lint`/`typecheck` in check.yml (owned by canonical-check-command.md / fail-fast-check-chain.md).
**Invariant:** the gate must never silently pretend to analyze TypeScript: the constraint is documented in-file, adjacent to the `linter:` line it explains, naming exactly where the real baseline moved. A future editor who "fixes" the linter to qodana-js without a license bump will hit the documented failure mode.
**Probe:** no direct test exists for qodana.yaml at this pin (recorded caveat); the workflow's trigger matrix and action pin are the observable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "qodana linter license community gate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: when a quality gate is license- or capability-constrained, keep the pipeline green with a deliberately mismatched engine AND document the constraint in-file next to the setting, naming exactly where the real baseline moved — never leave a green gate that implies coverage it does not have. Adapt the engine name and the real-baseline pointers to your stack. Omit nothing structural; the commented-out failureConditions block is a ready upgrade path, not dead config. No direct test coverage at this pin.
