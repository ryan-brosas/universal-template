<!-- capsule-v2 -->
# Structure, code style, and logging — is the repo organized by feature with enforced lint and prod-safe logs?

**Source:** project-guidelines §6 Structure, §7 Code style, §8 Logging. **Question:** Do folders, ESLint/Prettier, and logging follow elsewhen maintainability conventions?

## Structure seam
**Path/Symbol:** JavaScript project tree, build output.
**Signature:** feature folders; ./config ./scripts ./build.
**Data Shape:** product/index.js + product.test.js; not controllers/ models/ split.

### Decisive pattern
```
src/
  product/
    index.js
    product.js
    product.test.js
  config/
  scripts/
build/          # gitignored
```

**Flow:** organize by **feature/page/component**, not MVC **role** folders → **`./config`** module(s) fed by **env vars** — avoid separate config file per environment name → **`./scripts`** for node/bash tooling → output to **`./build`** or **`dist/`** and **gitignore** → colocate tests (see env-deps capsule).
**Invariant:** controllers/models split for small app, or committed build artifacts, fails structure review.
**Probe:** tree review; gitignore includes build/; config reads env not duplicated per stage file.

## Code style seam
**Flow:** **modern JS** syntax for greenfield; match legacy otherwise → **ESLint** in **build/CI** (Airbnb or project standard) + **`.eslintignore`** → remove **`eslint-disable`** before PR → **EditorConfig** + **Prettier** + **husky/lint-staged** precommit → searchable **verb** function names; **step-down** ordering in files → **`//TODO:`** or **`//TODO(#123)`** for deferred work → no funny/irrelevant names/comments.
**Invariant:** CI lint skipped or eslint-disable spam in PR fails style review.
**Probe:** npm run lint in CI; grep eslint-disable on changed files.

## Logging seam
**Flow:** no **client console.log** in production bundles — lint should warn → server: **winston/bunyan** structured logs with timestamps/rotation in prod.
**Invariant:** console.log in shipped client code or printf debugging in prod server paths fails logging review.
**Probe:** eslint no-console rule; prod log config review.

## Verdict
Feature-based layout, mechanical lint/format, production-safe logging. Learning note: `js-project-learning-note.md`.
