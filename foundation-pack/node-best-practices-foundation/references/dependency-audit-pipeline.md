<!-- capsule-v2 -->
# Dependency vulnerability scanning — npm audit baseline + auto-fix PRs, wired into CI not memory

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** How does a dependency tree stay clean as CVEs land after you ship?

## Audit CLI in the build; Snyk/Greenkeeper close the loop with automated fix PRs
**Path/Symbol:** `sections/security/dependencysecurity.md` (risk framing :5-7, npm audit :16-24, Snyk :26-37, Greenkeeper :39-48).
**Signature:** `npm audit` (NPM@6+) → report of affected package/severity/path/patch commands; Snyk CLI + GitHub app; Greenkeeper branch-per-update bot.
**Data Shape:** audit report fields: package name, severity, description, path, fix command.

### Decisive source
```text
// dependencysecurity.md :20 — what the baseline tool returns
Running `npm audit` will produce a report of security vulnerabilities with
the affected package name, vulnerability severity and description, path, and
other information, and, if available, commands to apply patches.
// :28 — why passive auditing is insufficient
Snyk ... automatically creates new pull requests fixing vulnerabilities as
patches are released for known vulnerabilities.
```

**Flow:** every Node app leans on deep transitive trees (:5) → new advisories publish continuously AFTER your lockfile freezes → periodic/build-time `npm audit` catches known-bad versions at gate time; Snyk-style integrations push upgrade PRs so fixes arrive as reviewable diffs rather than dashboard noise; Greenkeeper's variant runs your full CI per update so breakage surfaces as an issue with current-vs-updated version context (:43).
**Invariant:** the failure mode is staleness — a clean install today rots silently; the control is RECURRING (CLI schedule or build step), not one-shot. Detection without remediation flow leaves findings piling up unread; automation that opens PRs keeps humans reviewing instead of triaging.
**Probe:** no runner upstream. Deterministic probe: `grep -ic 'npm audit' sections/security/dependencysecurity.md` >= 5 && `grep -c 'Snyk\|Greenkeeper' sections/security/dependencysecurity.md` >= 6.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "vulnerable", "limit": 10}'
# resolves `sections/production/detectvulnerabilities.md`, `sections/security/dependencysecurity.md` line-exact (verified 2026-08-24)
```

## Production-plane twin (pass 3)
`sections/production/detectvulnerabilities.md` (:7-12) is the ops-side statement of the SAME contract — the tree is only as strong as its weakest link, and `npm audit` + `snyk` are the two named automatic detectors. Read both docs as one seam: security plane owns the pipeline mechanics, production plane owns the deployment-gate placement.

## Verdict
Adopt `npm audit` as a non-negotiable CI stage plus an auto-PR service where the project's risk profile justifies it. Adapt tooling (GitHub Dependabot is the modern equivalent). Omit ad-hoc manual audits except for incident response.
