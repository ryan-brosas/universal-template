<!-- capsule-v2 -->
# Docker build-cache layer ordering — which instruction order keeps builds cached, and what busts it?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** How must a Node.js Dockerfile be ordered so dependency installs stay cached across code-only changes?

## Stable→volatile ladder; one invalidated layer poisons all later layers
**Path/Symbol:** `sections/docker/use-cache-for-shorter-build-time.md` (explainer+warning :5, volatile-LABEL rule :13-25, system-packages-first :33-36, lockfile-first :38-45, copy+build-last :47-52, full example no-build :57-82, full example TS build :86-115).
**Signature:** `COPY "package.json" "package-lock.json" "./"` → `RUN npm ci` → `COPY . .` → `RUN npm run build` (:40-52).
**Data Shape:** Dockerfile = linear layer list; cache key per instruction = instruction text + input-file hashes; app code changes most often, manifests least.

### Decisive source
```text
# use-cache-for-shorter-build-time.md :5 — the invariant
The docker daemon can reuse those layers between builds if the instructions
are identical or in the case of a `COPY` or `ADD` files used are identical.
⚠️ If the cache can't be used for a particular layer all the subsequent
layers will be invalidated too. That's why order is important.
# :70-71 — deps before source
COPY "package.json" "package-lock.json" "./"
RUN npm ci --production
```

**Flow:** FROM base → apt/apk system packages (rarely change) → USER/WORKDIR → COPY manifests only → npm ci (cached until lockfile changes) → COPY source → build → final stage `COPY --from=builder` selected paths + `npm prune --production`.
**Invariant:** ANY invalidated layer invalidates every subsequent layer. `COPY . .` placed before `npm ci` re-downloads the whole tree on every source edit; a frequently-changing `LABEL build_number="483"` near the top (:17-25) defeats the entire file. System packages go first so gcc/make aren't reinstalled per build (:33-36); install only what production needs — "Do not install package only for convenience" (:36).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'package-lock.json' sections/docker/use-cache-for-shorter-build-time.md` >= 3 && `grep -c 'npm prune --production' sections/docker/use-cache-for-shorter-build-time.md` >= 2.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "use-cache-for-shorter-build-time", limit: 5 });` — resolves the Module node + README TL;DR lines (BM25 search_graph returns zero on this doc-shaped graph; use search_code).

## Verdict
Adopt the ordering ladder and the deps-before-source split verbatim. Adapt base image tags and package-manager equivalents (pnpm/yarn frozen lockfile installs). Omit the pinned node:10/alpine3.11 versions (superseded) and the builder-stage `--production` if you build dev deps for compilation — keep the final-stage `npm prune --production`.
