<!-- capsule-v2 -->
# Dependency lock & exact-install chain — how does a locked version survive into production?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What is the full lock→exact-install chain, and where does each link fail open?

## save-exact + committed package-lock.json + npm ci (fail-on-mismatch) — never bare npm install in prod
**Path/Symbol:** `sections/production/lockdependencies.md` (:7 explainer), (:13-16 .npmrc), (:20-46 lockfile shape), `sections/production/installpackageswithnpmci.md` (:7-12 ci guarantees, :14-16 manual-edit gap detection), `sections/production/LTSrelease.md` (:5-7 LTS definition), `sections/production/detectvulnerabilities.md` (:9-12 audit tools).
**Signature:** `.npmrc`: `save-exact:true`; commit `package-lock.json`; install via `npm ci`; run an LTS Node release (even-numbered, ≥18 months support).
**Data Shape:** npm ci contract: FAILS if package.json ⇄ package-lock.json mismatch or no lockfile; REMOVES existing node_modules first; ~2x faster than npm install.

### Decisive source
```text
# installpackageswithnpmci.md :10-12 — the three guarantees
* It will fail if your `package.json` and your `package-lock.json` do not
match (they should) or if you don't have a lock file
* If a `node_modules` folder is present it will automatically remove it
before installing
* It is faster! Nearly twice as fast according to the release blog post
```

**Flow:** save-exact pins direct deps at add-time → package-lock.json pins ALL transitive deps with integrity hashes (lockdependencies :20-46) → committing the lockfile makes every environment resolve identical versions → `npm ci` enforces manifest⇄lock equality at install, so CI/QA test EXACTLY what ships (:14-16: a hand-edited package.json throws instead of silently drifting) → all of it runs on an even-numbered LTS line for stability/security backports.
**Invariant:** bare `npm install` in deployment re-resolves ranges and can pull momentjs-2.1.5 where 2.1.4 was tested (:7) — the chain has NO substitute link. Locking addresses reproducibility only; known-CVE coverage needs the separate recurring audit pipeline (`dependency-audit-pipeline`, npm audit/snyk :9-12 here).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'save-exact' sections/production/lockdependencies.md` >= 1 && `grep -cF 'do not match' sections/production/installpackageswithnpmci.md` = 1 && `grep -c '18 months' sections/production/LTSrelease.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "save-exact", limit: 5 });`

## Verdict
Adopt the whole chain (exact-save → committed lock → ci-install → LTS runtime) as one unit — partial adoption gives false confidence. Adapt registry/mirror config around it. Omit npm-version history notes; treat lockfileVersion:1 examples as historical shape, current format differs.
