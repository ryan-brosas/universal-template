<!-- capsule-v2 -->
# Docker image slimming & tagging — what actually shrinks the image, and which `:latest` assumption bites?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which cleanup/shrink moves are safe, and how do implicit tag semantics betray an unpinned deploy?

## npm-cache cleanup with --force; minimal bases; :latest moves only on UNTAGGED builds
**Path/Symbol:** `sections/docker/clean-cache.md` (:7 rationale+CI trap, :9 multi-stage caveat, :19-26 command), `sections/docker/smaller_base_images.md` (:3-5 size ladder), `sections/docker/image-tags.md` (:5 default-tag trap, :9-18 build matrix, :22 blogger confirmation).
**Signature:** `RUN npm ci --production && npm cache clean --force`; `FROM node:<ver>-slim | -alpine`; `docker build -t company/image_name:0.1 .`
**Data Shape:** tens-of-MB recovered from the package cache; node full ~345MB vs alpine ~39MB (~10x) vs slim ~38MB; tag matrix — explicit-tag builds leave `:latest` untouched, an untagged build UPDATES `:latest`.

### Decisive source
```text
# clean-cache.md :7 — why --force is load-bearing
By removing this cache, using a single line of code, tens of MB are shaved
from the image. While doing so, ensure that it doesn't exit with non-zero
code and fail the CI build because of caching issues - This can be avoided
by including the --force flag.
# image-tags.md :9-18 — the matrix
$ docker build -t company/image_name:0.1 .   # :latest image is not updated
$ docker build -t company/image_name          # :latest image is updated
```

**Flow:** single-stage build → clean npm cache in the SAME RUN (else the cache lives in its own layer and nothing shrinks) → pull minimal base (alpine/slim tradeoff: minimal images may lack native-build toolchains and curl, smaller_base_images :3).
**Invariant:** `npm cache clean` without `--force` can exit non-zero and fail CI (:7). Cache cleaning is pointless in a multi-stage build UNLESS the final stage installs packages itself (:9). `:latest` is Docker's DEFAULT tag — relying on it as "newest prod" is false; pin explicit versions and promote by digest.
**Probe:** no runner upstream. Deterministic probe: `grep -cF 'cache clean --force' sections/docker/clean-cache.md` >= 1 && `grep -cF ':latest' sections/docker/image-tags.md` >= 3 && `grep -c 'Alpine' sections/docker/smaller_base_images.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "image-tags", limit: 5 });`

## Verdict
Adopt --force cache-clean in single-stage images, the slim/alpine default for runtime images, and explicit mutable-version tags with digest promotion. Adapt sizes to current Node release lines (the 345MB figure is doc-era). Omit `:latest` reliance entirely — including "latest is newest" tooling assumptions.
