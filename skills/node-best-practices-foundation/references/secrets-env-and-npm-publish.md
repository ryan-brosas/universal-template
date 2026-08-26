<!-- capsule-v2 -->
# Secrets-out-of-config litmus — process.env default, encrypted-at-rest exception, and the .npmignore override trap

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Where do credentials live, and which publish path leaks them anyway?

## Env-vars-first; cryptr only for must-commit secrets; git-secrets audits history
**Path/Symbol:** `sections/security/secretmanagement.md` (:3-10 explainer, env example :16-21, cryptr example :23-32) + `sections/security/avoid_publishing_secrets.md` (.npmignore vs files array :4-8, examples :11-36).
**Signature:** `process.env.KEY` read path; `new Cryptr(process.env.SECRET)` + `cryptr.decrypt(cipherText)` for the exception case.
**Data Shape:** 12-factor config: env vars per deploy; `.npmignore` blacklist OR `package.json` `"files"` whitelist govern what npm publish ships.

### Decisive source
```text
// secretmanagement.md :6 — the litmus test
A litmus test for whether an app has all config correctly factored out of the
code is whether the codebase could be made open source at any moment, without
compromising any credentials.
// avoid_publishing_secrets.md :8 — THE OVERRIDE TRAP
if a project is utilising both .npmignore and .gitignore files, everything
which isn't in .npmignore is published to the registry (i.e. the .npmignore
file overrides the .gitignore).
```

**Flow:** secrets → env vars → `process.env` at runtime; nothing sensitive ever hits source control. Rare must-commit values get symmetric encryption via cryptr with the KEY itself in env. git-secrets-style hooks scan commits/messages for accidental additions (:10).
**Invariant:** two silent-leak paths a porter misses: (1) `.npmignore` OVERRIDES `.gitignore` — a file ignored from git can still ship in the published tarball if you forget to also ignore it there; developers "update the .gitignore file, but forget .npmignore" (:8); (2) when BOTH `files` array and ignore-file exist, `files` wins (:41). Verify intent with `npm publish --dry-run` before first publish (:6).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'process.env' sections/security/secretmanagement.md` >= 2 && `grep -c 'file overrides' sections/security/avoid_publishing_secrets.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "file overrides", "limit": 10}'
# resolves `sections/security/avoid_publishing_secrets.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the open-source litmus test as the config-review gate and the dry-run-before-publish rule. Adapt encryption tooling freely. Omit vault products here (covered by OWASP checklist capsule) — this capsule owns the code-level paths.
