<!-- capsule-v2 -->
# OpenAPI src artifact class — what is `lib/src/pycharm-openapi-src`, and how must it be treated differently from every other plane?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What is the loose `lib/src/pycharm-openapi-src/` tree (plus `.zip` twin), why does an Apache-2.0 source tree ship inside a proprietary install, and why is it the ONLY graph-retrievable source plane in these builds?

## Connected graph-selected seam
**Path/Symbol:** `/lib/src/pycharm-openapi-src/**` (222 `.java` + 49 `.kt`, ~8.7k LOC) + twin `lib/src/pycharm-openapi-src.zip`.
**Signature:** directory of full package paths under `com/jetbrains/python/**`; each file carries an Apache-2.0 license header inside the otherwise proprietary distribution.
**Data Shape:** cluster distribution: pycharm AND dataspell ship the plane (`<install>/lib/src/`), the other 13 installs do not. pycharm zip = 271 entries / md5 `027287ffb717658e4ecce9c9289417c1`; dataspell zip = 269 entries / md5 `7995ec4e721e2c3bb40071fea7a3cbbe` — an OLDER snapshot (its `PyPackageManager.java` header says 2000-2021 vs pycharm's 2000-2024). Loose tree ↔ zip contents verified IDENTICAL for pycharm (`comm` set-diff zip-vs-disk: both directions EMPTY).

### Decisive source
```
$ unzip -l lib/src/pycharm-openapi-src.zip | tail -1
   425857    271 files
$ comm -23 jb_zip.txt jb_disk.txt | wc -l && comm -13 jb_zip.txt jb_disk.txt | wc -l
0
0
$ head -1 com/jetbrains/python/packaging/PyPackageManager.java
// Copyright 2000-2024 ... Apache 2.0 license ...
```

**Flow:** JetBrains publishes the Python-plugin OPEN api as real sources next to the compiled platform (the "openapi" contract surface third-party plugins compile against) → dataspell (a pycharm derivative on the DS-261 train) carries its own older copy → the rest of the cluster omits it entirely.
**Invariant:** treat this tree as the authoritative citable SOURCE plane for Python-plugin extension contracts — unlike jar interiors (XML/resources, retrievable only via unzip probes), these files are symbol-indexed by Codebase Memory, so `search_graph`/`get_code_snippet` return real line-exact spans here. Cite the pycharm copy (newest snapshot); never mix citations across the two snapshots (dataspell's is stale by ~3 years of headers).
**Probe:** from `<install>` root (anchored at `pycharm/`):
`ls lib/src/pycharm-openapi-src/com/jetbrains/python/packaging/ | wc -l` → `9`;
`find lib/src/pycharm-openapi-src -name '*.java' | wc -l` → `222`;
`ls /mnt/hdd/utopia/inspo/reference/jetbrains/clion/lib/src 2>/dev/null | wc -l` → `0` (plane absent outside py/dataspell).
**Coverage caveat:** zip↔disk identity verified for pycharm only; assume drift if either snapshot changes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "StubAwareComputation overAst overStub compute", limit: 10, fields: ["signature", "name", "file"] });
// rank-1..4 all resolve into lib/src/pycharm-openapi-src/.../StubAwareComputation.java :157/:170/:120/:127
```

## Verdict
Adopt: this is the readable contract surface of the Python plugin — mine interfaces/EPs here, cite file:line directly. Adapt: snapshot choice (pin pycharm's). Omit: assuming other products share it (13 of 15 don't).
