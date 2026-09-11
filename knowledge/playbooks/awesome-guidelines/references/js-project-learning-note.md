# JavaScript project guidelines — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `js-project-*.md` capsules, `javascript-project-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [elsewhencode/project-guidelines](https://github.com/elsewhencode/project-guidelines) README (primary) | Git workflow, docs, env/config, deps, testing, structure, ESLint, logging, REST API, a11y baseline, licensing |
| [README.sample.md](https://github.com/elsewhencode/project-guidelines/blob/master/README.sample.md) (primary template) | README sections: install, dev, build, deploy, tests, style, API, DB, license |
| [config.sample.js](https://github.com/elsewhencode/project-guidelines/blob/master/config.sample.js) / configWithTest (secondary) | env vars from process.env; joi validation at startup |
| `git-workflow-and-versioning` (secondary) | Conventional commits — elsewhen uses 50/72 + imperative (compatible) |
| `api-design-practices` (secondary) | REST overlap — elsewhen adds JS camelCase JSON + List suffix convention |
| `node-coding-practices` / `javascript-coding-practices` (secondary) | Line-level JS style — project-guidelines adds repo/process layer |
| `wcag-accessibility-practices` (secondary) | Deep WCAG — elsewhen adds lighthouse/axe/linter setup at project start |

**Scope:** **JavaScript/Node web project** setup — repo layout, workflow, tooling, API conventions, not language syntax alone.

## Mental model

Elsewhen treats maintainability as **process + structure + conventions**:

1. **Git & docs** — feature branches from `develop`; PR-only merges; rebase; good commits; README template; meaningful comments.
2. **Env, deps, test** — env vars not constants; lockfile; engines/nvm; colocated `*.test.js`; pure testable code.
3. **Structure & style** — feature folders not MVC role folders; `./config`, `./scripts`, `./build`; ESLint+Prettier+hooks; no prod console.log.
4. **API, a11y, verify** — REST resource URLs; machine-readable errors; API security basics; lighthouse/axe from day one.

## Decision tables

### Git (§1)

| Topic | Rule |
|---|---|
| Branching | Feature branch from `develop`; never push direct to `develop`/`master` |
| Merge | PR after rebase onto `develop`; delete branch after merge |
| Pre-PR | Build + tests + lint pass |
| Commits | 50-char subject, 72 wrap body; imperative mood; what/why in body |
| Protection | Protect `develop` and `master` |

### Documentation (§2)

| Topic | Rule |
|---|---|
| README | Use README.sample.md template; keep updated |
| Comments | Explain intent; link discussions; remove stale/commented-out code |
| Balance | Comments don't excuse bad code; clean code doesn't excuse zero comments |

### Environments (§3)

| Topic | Rule |
|---|---|
| Stages | Separate dev/test/production configs |
| Secrets | Env vars only — never constants in repo; `.env` gitignored; `.env.example` committed |
| Validation | Validate env at startup (e.g. joi) |
| Node | `engines` in package.json + `.nvmrc`; optional preinstall version check |
| Docker | Prefer for consistent dev |
| Lockfile | `package-lock.json` (npm 5+) or yarn lock — same deps for all |

### Dependencies (§4)

| Topic | Rule |
|---|---|
| Hygiene | `npm ls`, depcheck for unused |
| Selection | Check npm stats, maintainer activity; team discuss obscure deps |
| Updates | `npm outdated`; one-at-a-time; read release notes; Snyk for CVEs |

### Testing (§5)

| Topic | Rule |
|---|---|
| Mode | Separate test environment when needed |
| Placement | `module.test.js` beside module; `__tests__` for non-colocated |
| Code | Pure functions; minimize side effects |
| Types | Static checker (Flow/TS) recommended |
| Pre-PR | Run tests locally after rebase |

### Structure (§6)

| Topic | Rule |
|---|---|
| Layout | By feature (`product/`, `user/`) not role (`controllers/`) |
| Config | Single `./config` folder; values from env — not per-env config files |
| Scripts | `./scripts` for bash/node tooling |
| Build | `./build` or `dist/` gitignored |

### Code style (§7)

| Topic | Rule |
|---|---|
| Syntax | Modern JS for new projects; match legacy otherwise |
| Lint | ESLint in build; Airbnb or project standard; `.eslintignore` |
| Format | EditorConfig + Prettier + lint-staged/husky |
| Names | Searchable; functions verb phrases; step-down rule in files |
| TODO | `//TODO:` or `//TODO(#ticket)` |

### Logging (§8)

| Topic | Rule |
|---|---|
| Client | No console.log in production |
| Server | winston/bunyan structured logs in prod |

### API (§9)

| Topic | Rule |
|---|---|
| URLs | kebab-case plural nouns; no verbs in resource paths |
| JSON | camelCase properties; `List` suffix for collections in code |
| HTTP | CRUD via methods; nested `/schools/2/students/31` |
| Version | `/v1/...` leftmost |
| Errors | `{ code, message, description }`; generic auth errors |
| Status | Common subset: 200/201/204/400/401/403/404/500 |
| Pagination | limit/offset; optional `fields` filter |
| Security | Bearer in Authorization header; HTTPS only; rate limit; helmet; validate Content-Type; safe JSON serialize |
| Docs | README API section; Swagger/ApiBlueprint |

### Accessibility (§10)

| Topic | Rule |
|---|---|
| Start | lighthouse/axe audits from project start; agree min score |
| Lint | eslint-plugin-jsx-a11y (React) or framework equivalent |
| Rules | alt text, heading order, contrast, link names, semantic lists |
| Deep | pair `wcag-accessibility-practices` for WCAG AA |

### Licensing (§11)

| Topic | Rule |
|---|---|
| Rights | MIT/Apache/BSD for libs; respect image/video copyright |

## Anti-patterns

- Push directly to develop/master
- Secrets in source or committed `.env`
- No lockfile / mismatched dependency versions
- MVC role folders for small apps
- Separate config files per environment name
- Committed build output
- eslint-disable left in PR
- Commented-out dead code blocks
- console.log in production client bundles
- Verbs in REST resource URLs (`/getUsers`)
- DB table names in public API URLs
- Tokens in query strings
- HTTP API endpoints (non-TLS)
- Skipping a11y until late; no automated a11y in CI
- README never updated after scaffold

## Skill trace

| Artifact | Role |
|---|---|
| `js-project-git-docs.md` | git + README + comments |
| `js-project-env-deps-test.md` | env, lockfile, testing |
| `js-project-structure-style.md` | folders, ESLint, logging |
| `js-project-api-a11y-verify.md` | REST API, a11y setup, verify |
| `javascript-project-practices/SKILL.md` | JS project bootstrap/review |

## Relation to sibling skills

| project-guidelines | dedicated skill |
|---|---|
| Git rebase/PR flow | `git-workflow-and-versioning` |
| REST API details | `api-design-practices` |
| Line JS style | `javascript-coding-practices`, `node-coding-practices` |
| WCAG depth | `wcag-accessibility-practices` |
| API security detail | `webappsec-coding-practices` |
