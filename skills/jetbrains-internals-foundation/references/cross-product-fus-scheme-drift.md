<!-- capsule-v2 -->
# Cross-product FUS scheme drift — how does one event vocabulary fork per IDE without breaking the shared platform?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` + sibling installs. **Question:** When every product ships its own copy of a 700-group telemetry scheme, what drifts, what stays identical, and how do you detect a product-specific addition without diffing megabytes?

## Connected graph-selected seam
**Path/Symbol:** `event-log-metadata/FUS/events-scheme.json` in EVERY branded product jar: pycharm `intellij.pycharm.community.jar` (v7613, 716 groups), webstorm `intellij.webstorm.jar` (v7584, 697), rider `intellij.rider.ide.jar` (v7505, **872**), clion `intellij.clion.main.nolang.jar` (v7583, 816), goland `intellij.goland.jar` (v7598, 710), phpstorm `intellij.php.resources.jar` (v7598, **719** — the ONLY product carrying the plane in a resources jar, not the branded app jar), rubymine `intellij.rubymine.jar` (v7598, 713), rustrover `intellij.rustrover.jar` (v7593, 661), dataspell `app.jar` (v7462, 717 @ DS-261 older train), datagrip `intellij.datagrip.jar` (v6989, 625 — earliest train), mps `app.jar` (v7332, 746).
**Signature:** scheme `version` values cluster by TRAIN (262-line ≈ 7500–7613; DS-261 = 7462; MPS-261 = 7332; DB-262 = 6989 outlier) while group COUNTS vary freely per product.
**Data Shape:** py-vs-ws overlap: 689 common groups, py-only 27 (`com.laravel-idea.events`, `data.wrangler`, `databricks.features`, `ds.sql.cell`, `jupyter.py.features`, `llm.python.action.events` …), ws-only 8. Rider-only groups are domain-marked (`dotnet.actions`, `dotnet.bulb`, `diagram.usages.trigger`, `deployment.servers` …).

### Decisive source
Common-group drift is ADDITIVE-ONLY. All 14 differing py/ws common groups keep identical rule KEYS and versions — they differ only in extra `event_data` fields, e.g.:
```
GROUP code.provenance   py adds .event_data.ai_percentage=[{regexp#float}]
                        py adds .event_data.total_lines_changed=[{regexp#integer}]
GROUP debugger.logpoints.usage  py adds .lang=[{util#lang}] + .lifetime_mean_ms
GROUP fus.event.log     py adds .deleted_file_age_ms / .build_type enum EAP|RELEASE|UNKNOWN|ALL
```
(verified by flattened key-set diff over all 689 common groups).

**Flow:** products inherit the platform corpus then append product groups AND product fields on shared groups; because field lists are UNIONS (fus-events-scheme-grammar), an added field can't invalidate another product's events — this is why per-product forks stay merge-compatible upstream.
**Invariant:** NEVER assume "same group id ⇒ same rules" across jars (14/689 differ for py-ws); but DO assume key-shape stability (zero rule-key divergences found). Detection recipe: compare GROUP ID SETS first (cheap id diff localizes product additions), only then flatten-diff the intersected ids.
**Probe:** from `pycharm/` install root (paths relative to one product; siblings via `../<product>/lib/…`):
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '"version":"[0-9]*"'` → `"version":"7613"`;
`unzip -p ../webstorm/lib/intellij.webstorm.jar event-log-metadata/FUS/events-scheme.json | grep -o '"version":"[0-9]*"'` → `"version":"7584"`;
group-count probe: `unzip -p <jar> event-log-metadata/FUS/events-scheme.json | grep -o '"event_id"' | wc -l` → py `716` / rider `872`.
**Coverage caveat:** jar resource plane — not graph-indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target (adjudicated wrong-plane). Deterministic retrieval: the version+count two-number fingerprint above identifies any product's scheme generation without extracting full JSON.

**Complements:** event-log-metadata-family-layout (family set IS stable even as groups drift); release-train-platform-identity (jar-level md5 method — this capsule is its content-level analog).

## Verdict
Adopt: additive-only schema forking with union-tolerant field lists; audit by id-set diff before content diff. Adapt the fingerprint method to your fleet. Omit per-product group catalogs (inventory data, not pattern).
