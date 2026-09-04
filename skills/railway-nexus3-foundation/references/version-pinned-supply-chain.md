<!-- capsule-v2 -->
# Version-pinned supply chain — why is the base image digest-pinned AND the exact upstream version restated across every human-facing file?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does a deployment template keep its upstream dependency from drifting, and which artifacts must move TOGETHER on a version bump?

## Digest pin + cross-file version census
**Path/Symbol:** `Dockerfile:1` (digest pin), `Dockerfile:6` (`EXPOSE 8081`), `tests/static.mjs:1` (regex pins), `README.md:5`, `TEMPLATE_README.md:5`, `THIRD_PARTY_NOTICES.md:3`.
**Signature:** `FROM docker.io/sonatype/nexus3:3.95.2-alpine@sha256:adb4539e29bcb1c91e5545c853f6c74da5e57efd4c243aa4d5454f309904ab13` — tag AND sha256 digest; the static test asserts the regex `/nexus3:3\.95\.2-alpine@sha256:[a-f0-9]{64}/` and `assert.doesNotMatch(d,/:latest/)`.

### Decisive source
```dockerfile
FROM docker.io/sonatype/nexus3:3.95.2-alpine@sha256:adb4539e29bcb1c91e5545c853f6c74da5e57efd4c243aa4d5454f309904ab13
```
(`Dockerfile:1` VERBATIM at pin; `tests/static.mjs:1` asserts the format regex `/nexus3:3\.95\.2-alpine@sha256:[a-f0-9]{64}/` and `assert.doesNotMatch(d,/:latest/)`.)

**Flow:** image identity = tag+digest (immutable bytes, no silent upstream drift) → the SAME version string is restated in README (:5), TEMPLATE_README (:5), and THIRD_PARTY_NOTICES (:3) as marketing/legal/compat claims that must not contradict the built artifact.
**Invariant:** a porter who bumps only the Dockerfile leaves three files asserting a version nobody ships — support-facing lies. The template treats "what version do we run" as ONE fact with FOUR carriers (Dockerfile, README, TEMPLATE_README, THIRD_PARTY_NOTICES); a version bump is a coordinated four-file change, and `tests/static.mjs`'s digest-format regex is the tripwire that at least the Dockerfile half cannot rot silently.
**Probe:** EXECUTED this pass: `node tests/static.mjs` rc=0 ("static template checks passed"). Census anchors (executed): `grep -o '3\.95\.[0-9]' Dockerfile | wc -l` = 1, same for README.md = 2, TEMPLATE_README.md = 1, THIRD_PARTY_NOTICES.md = 2, tests/static.mjs = 0 (asserts FORMAT, never hardcodes 3.95.2 — deliberate: format-only assertion survives minor bumps without edits), package.json = 0 (template's own version independent of upstream). Negative pin: `grep -cF ':latest' Dockerfile` = 0.

## Get live surrounding code
**Retrieve:** BM25 misses Dockerfile tokens (live total:0 for "digest sha256 pinned image"); search_code resolves both carriers:
```
codebase-memory-mcp cli search_code '{"project":"railway-template-nexus3","pattern":"nexus3","limit":6}'
```
→ Module `Dockerfile` L1-8 match `"1"` + Variable `tests.static.d` in `tests/static.mjs` L1 match `"1"` (verified this pass).

## Verdict
Adopt: digest-pin the base image, forbid `:latest`, restate the version across every doc carrier, and assert the digest FORMAT (not the literal) in static tests so minor bumps don't break CI. Adapt registry/product names per target. Omit nothing — the four-carrier census is the portable core.
