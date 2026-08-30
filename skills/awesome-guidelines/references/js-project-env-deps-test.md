<!-- capsule-v2 -->
# Environment, dependencies, and testing — are config, lockfiles, and tests project-grade?

**Source:** project-guidelines §3 Environments, §4 Dependencies, §5 Testing. **Question:** Do secrets stay out of code, deps stay pinned, and tests live beside modules?

## Environment seam
**Path/Symbol:** Node app config bootstrap, package.json engines.
**Signature:** env vars via process.env; joi validation; .env.example committed.
**Data Shape:** dev/test/production stages; engines + .nvmrc.

### Decisive pattern
```javascript
// config — values from env, validated at startup
const schema = Joi.object({ PORT: Joi.number().default(3000), DATABASE_URL: Joi.string().required() });
// .env gitignored; .env.example committed
```

**Flow:** separate **dev/test/production** behavior → load secrets and URLs from **environment variables** — never hard-coded constants → **`.env`** gitignored; commit **`.env.example`** → **validate env at startup** (joi) before serving → pin Node via **`engines`** + **`.nvmrc`**; optional **preinstall** version guard → prefer **Docker** for consistent dev → use **local** npm tools not global installs.
**Invariant:** API keys in source, missing env validation, or no lockfile fails environment review.
**Probe:** grep `process.env` vs literal secrets; `.env.example` diff; `engines`/`package-lock.json` present.

## Dependencies seam
**Flow:** track deps with **`npm ls --depth=0`** → **`depcheck`** unused packages → evaluate new deps: download stats, maintainer cadence, team approval for obscure libs → update with **`npm outdated`** one package at a time + release notes → **Snyk**/audit for CVEs.
**Invariant:** unpinned or un-audited dependency drift on production app fails dependency review.
**Probe:** lockfile committed; npm audit in CI; depcheck clean on changed packages.

## Testing seam
**Flow:** separate **test environment** when prod analytics/rate limits would interfere → colocate **`*.test.js`/`*.spec.js`** next to module; **`__tests__`** for integration-only → write **pure, testable** functions; static types (TS/Flow) optional boost → run **`npm test`** locally after rebase and before PR → document test commands in README.
**Invariant:** no tests on changed business logic or tests only in distant folder without reason fails testing review.
**Probe:** test file placement; CI test job; README test section.

## Verdict
Env-driven config, locked deps, colocated tests, pre-PR local verify. Learning note: `js-project-learning-note.md`.
