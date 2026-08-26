<!-- capsule-v2 -->
# Docker context/lint/scan gate — what stands between the build context and a production image?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which sequential gates must a Node image pass (context filtering → Dockerfile lint → image scan), and what does each catch that the previous misses?

## Three gates: .dockerignore secrets filter, hadolint structure lint, trivy-class final scan
**Path/Symbol:** `sections/docker/docker-ignore.md` (:7 dual benefit, :16-28 default ignore list, :34-48 COPY-all anti-pattern), `sections/docker/lint-dockerfile.md` (:5 failure classes, :12-15 flags), `sections/docker/scan-images.md` (:7 why code-scan isn't enough + scanner families + threshold advice, :17-21 trivy run), `sections/docker/generic-tips.md` (:7-27 six language-agnostic rules).
**Signature:** `.dockerignore` entries `**/.env`, `**/.aws`, `**/.npmrc`, `**/.git`, `**/coverage`, `**/dist`; `hadolint --ignore DL3003 --ignore DL3006 <Dockerfile>`; `hadolint --trusted-registry my-company.com:500 <Dockerfile>`; `trivy image [YOUR_IMAGE_NAME]`.
**Data Shape:** gate 1 filters the build CONTEXT (files); gate 2 lints the RECIPE (instructions); gate 3 scans the ASSEMBLED artifact (OS binaries + layers).

### Decisive source
```text
# docker-ignore.md :7 — the dual purpose
development and CI folders contain secrets like .npmrc, .aws, .env files...
include a .dockerignore file that acts as the last safety net... Doing so
also boosts the build speed - By leaving out common development folders...
# scan-images.md :7 — why gate 3 exists at all
vulnerabilities also exist on the OS level and the app might execute those
binaries like Shell, Tarball, OpenSSL. Also, vulnerable dependencies might
be injected after the code scan (i.e. supply chain attacks)... these
scanners cover a lot of ground and therefore will show findings in almost
every scan - consider setting a high threshold bar
```

**Flow:** COPY . . sends EVERYTHING to the daemon over the wire (:34-48 anti-pattern) → ignore list drops dev/secret files → hadolint catches structural faults (copy from non-existent stage, unknown remote FROM, running as root/sudo — :5) → post-build, scan the FINAL image (Trivy/Anchore/Snyk classes: local-CI binary, cloud service, in-build scanner) with an explicit severity threshold policy.
**Invariant:** the three gates compose — skipping context filtering leaks secrets into layers even if you scan later; scanning code alone misses OS-level CVEs and post-scan supply-chain injection. Generic-tips companions: COPY over ADD (remote-fetch surface), no apt-get upgrade in build (non-reproducible + privilege demand), unprivileged `node` user, Dive inspection, Notary content trust.
**Probe:** no runner upstream. Deterministic probe: `grep -c '\*\*/\.aws' sections/docker/docker-ignore.md` >= 1 && `grep -c hadolint sections/docker/lint-dockerfile.md` >= 2 && `grep -icE 'triv[vy]' sections/docker/scan-images.md` >= 2.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "hadolint", limit: 5 });`

## Verdict
Adopt the gate ORDER and the default ignore list verbatim; wire hadolint + a scanner into CI with an explicit threshold. Adapt scanner choice to your CI vendor's plugin ecosystem. Omit specific tool versions; treat the "high threshold bar" advice as policy input, not a license to skip triage.
