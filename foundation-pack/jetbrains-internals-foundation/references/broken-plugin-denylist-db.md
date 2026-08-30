<!-- capsule-v2 -->
# Per-build broken-plugin denylist — how does an IDE refuse known-bad marketplace plugins?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (file explicitly not-indexed: `bin/brokenPlugins.db` listed under ignored-suffix in index_status). **Question:** How are incompatible third-party plugin versions blocked without shipping a code change?

## Connected graph-selected seam
**Path/Symbol:** `<install>/bin/brokenPlugins.db` (binary key-value blob, ~1 per product).
**Signature:** n/a (opaque data file; strings-readable).
**Data Shape:** header line = the OWNING build string (`PY-262.9437.214`, `WS-262.9437.145`, `RD-262.8665.400` — verified byte-exact per install), followed by a compact table: plugin id → list of broken version strings (18,427 lines via `strings` on pycharm's copy; e.g. `>me.drakeet.plugin.multitype` then versions `1.0.0…1.4.0`).

### Decisive source
```
$ strings bin/brokenPlugins.db | head -6
PY-262.9437.214
27818
24627
$35e38c06-9762-11e5-8dd3-54a050ace290
>me.drakeet.plugin.multitype
1.0.0
```
Cross-product headers:
`strings webstorm/bin/brokenPlugins.db | head -1` → `WS-262.9437.145`;
`strings rider/bin/brokenPlugins.db | head -1` → `RD-262.8665.400`.

**Flow:** platform loads the db at plugin-repository sync/enable time → any marketplace plugin whose id+version pair appears is refused (or downgraded) BEFORE classloading → the file is regenerated per release train, so the denylist is a VERSIONED ARTIFACT, not a global one.
**Invariant:** the header build string must equal the installing product's build — a porter reusing the mechanism MUST regenerate per release or stale entries silently block good plugins.
**Probe:** from `<install>` root: `strings bin/brokenPlugins.db | head -1` prints exactly `PY-262.9437.214` (pycharm) / `WS-262.9437.145` (webstorm); `test -f bin/brokenPlugins.db && echo DB-PRESENT`.
**Coverage caveat:** binary file deliberately excluded from the graph index (`ignored-suffix`) — strings-level probes only.

## Get live surrounding code
**Retrieve:** graph does NOT cover this file by design (index_status not_indexed.files lists it). Deterministic probes above ARE the retrieval path; no BM25 target exists.

## Verdict
Adopt: per-release compiled denylist keyed by plugin id+version with self-identifying build header. Adapt: your host's plugin metadata model and refusal UX. Omit: JetBrains' server-side generation pipeline (not shipped). New plane: complements experimental-feature-gating (feature flags) and fus-collector-registration (telemetry allowlists) as the third shipped "deny-by-default" catalog.
