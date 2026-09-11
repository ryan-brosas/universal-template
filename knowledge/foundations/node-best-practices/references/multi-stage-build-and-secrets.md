<!-- capsule-v2 -->
# Multi-stage build + build-secret hygiene — how do you ship only runtime artifacts and keep build-time secrets out of the image?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What Dockerfile structure separates build from runtime, and how do you pass an npm token without leaking it into the image?

## Build stage → copy only needed artifacts; secrets via --secret or multi-stage-with-delete
**Path/Symbol:** `sections/docker/multi_stage_builds.md` (explainer :3, example :7+) + `sections/docker/avoid-build-time-secrets.md` (secret mount :13-18, multi-stage :20-31, anti-pattern :33-43) + `sections/docker/install-for-production.md` (:22).
**Signature:** `FROM node:14.4.0 AS build` → build → `FROM node:slim-14.4.0` → `COPY --from=build /home/node/app/dist … ./` → `RUN npm ci --production`. Secrets: `RUN --mount=type=secret,id=npm,target=/root/.npmrc npm ci` (Docker buildkit) OR `ARG NPM_TOKEN` + write `.npmrc` + `rm -f .npmrc` in the SAME RUN layer.
**Data Shape:** multi-stage keeps build-only deps (TypeScript CLI, devDependencies) and build-time env vars out of the final image. The anti-pattern (:33-43) shows `ARG NPM_TOKEN` + `.npmrc` in a SINGLE-stage Dockerfile: deleting `.npmrc` in the same RUN "will not save it inside the layer, however it can be found in image history" — the token persists in the layer and registry history.

### Decisive source
```dockerfile
# avoid-build-time-secrets.md :20-31 — multi-stage keeps token out of final image
FROM node:12-slim AS build
ARG NPM_TOKEN
WORKDIR /usr/src/app
COPY . /dist
RUN echo "//registry.npmjs.org/:_authToken=$NPM_TOKEN" > .npmrc && \
    npm ci --production && \
    rm -f .npmrc
FROM build as prod
COPY --from=build /dist /dist
CMD ["node", "index.js"]
# note: ARG + .npmrc won't appear in the final image but live in the
# Docker daemon's un-tagged image list — delete those (build history).
```

**Flow:** build stage installs everything (incl. dev deps / build tools) → runtime stage copies only compiled output + lockfile → `npm ci --production` fetches only prod deps → secrets either mounted only during build (buildkit `--secret`, zero traces) or written-and-deleted within a build stage (leaves history, acceptable for most orgs).
**Invariant:** (1) devDependencies must not ship — "many of the infamous npm security breaches were found within development packages (e.g. eslint-scope)" (README 8.5). (2) a secret passed as a build arg persists in image layers/history unless removed in a separate stage or via `--secret`. (3) `npm ci` (not `npm install`) guarantees a clean, lockfile-exact install (install-for-production.md :22).
**Probe:** no runner upstream. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'rm -f .npmrc' sections/docker/avoid-build-time-secrets.md` = 2 (multi-stage + anti-pattern) and `grep -c -- '--from' sections/docker/multi_stage_builds.md` = 3. ERRATUM: the original second clause pinned the literal `COPY --from=build`, which appears ZERO times in this doc at this pin — all three stage-copy lines are `COPY --chown=node:node --from=build …`; anchor the grep on the flag (`--from`), not on an assumed stage name.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "rm -f .npmrc", "limit": 10}'
# resolves `sections/docker/avoid-build-time-secrets.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt multi-stage + prod-only install + secret hygiene for any containerized build. Adapt the secret mechanism (buildkit `--secret` vs Vault-injected) and base images. Omit the experimental-flag caveat (buildkit `--secret` is stable now).
