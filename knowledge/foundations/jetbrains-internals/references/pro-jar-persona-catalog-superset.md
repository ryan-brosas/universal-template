<!-- capsule-v2 -->
# Pro-jar persona catalog superset — how does one binary serve both Community and Professional analytics identities?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** When a product ships as community+pro jars in ONE install, which telemetry scheme does the running IDE use — and how do you tell them apart without unzipping both?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/lib/intellij.pycharm.community.jar` vs `lib/intellij.pycharm.pro.jar` — BOTH carry `event-log-metadata/FUS/events-scheme.json` with DIFFERENT content: community md5 `cbe6959ec954a72c7b6db9b86fe57d8c` vs pro md5 `f4d5bf618a9758f402324eb7af56d9b3`.
**Signature:** pro = 749 groups, community = 716; pro is a strict SUPERSET plus one swap.
**Data Shape:** pro-only groups (+34): the paid-feature catalog — bigdatatools.* ×11 (hadoop.monitoring, spark.monitoring/submit/configurations, zeppelin.interpreter/notebook/bindings …), datalore.actions/meta, django.manage.py.usage / django.structure.usage / django.template.live.preview, js.eslint.options/js.settings/js.live.edit.options/js.tslint.options/js.language.service, jupyter.vars, llm.projectWizard, python.plots, python.professional, pycharm.full.line.completion.feedback.survey, appcds, bdt.connection/bdt.stateviewer, aitoolkit.helperPlugin. community-only (−1): `pycharm.community.to.unified.promo` — the upgrade-nudge event exists ONLY in the free persona.

### Decisive source
```
unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | md5sum
→ cbe6959ec954a72c7b6db9b86fe57d8c  -
unzip -p lib/intellij.pycharm.pro.jar    event-log-metadata/FUS/events-scheme.json | md5sum
→ f4d5bf618a9758f402324eb7af56d9b3  -
```
group-id set diff: pro ⊇ community minus {pycharm.community.to.unified.promo} plus the 34 paid-domain groups.

**Flow:** the launcher's classpath slice decides identity (multi-persona-launcher-matrix): whichever jar loads first owns the active scheme, so a PyCharm Professional session reports against the 749-group catalog including django/js/bigdata events that can never fire in Community — while the promo group's absence in pro prevents the upgrade funnel from logging in the product it sells.
**Invariant:** scheme files are PERSONA artifacts, not per-plugin registries — each branded jar carries its whole persona catalog even when most groups belong to plugins shipped elsewhere; the md5 pair + count delta (749−716=33 net = +34 −1) fingerprints the split. Same pattern cluster-wide: every product's "branded" jar is the one carrying its FUS plane (phpstorm's lives in intellij.php.resources.jar).
**Probe:** from `<install>` root:
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '"event_id"' | wc -l` → `716`;
`unzip -p lib/intellij.pycharm.pro.jar event-log-metadata/FUS/events-scheme.json | grep -o '"event_id"' | wc -l` → `749`;
`unzip -p lib/intellij.pycharm.pro.jar event-log-metadata/FUS/events-scheme.json | grep -c '"python.professional"'` → `1` (pro marker);
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -c 'community.to.unified.promo'` → `1` (community marker; zero in pro).
**Coverage caveat:** jar resource plane — not graph-indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target (adjudicated wrong-plane). Deterministic retrieval:
`for j in lib/intellij.pycharm.community.jar lib/intellij.pycharm.pro.jar; do echo $j $(unzip -p $j event-log-metadata/FUS/events-scheme.json | md5sum | cut -c1-8); done`.

**Complements:** multi-persona-launcher-matrix (classpath-slice identity), cross-product-fus-scheme-drift (per-product forks — this capsule is the WITHIN-product analog).

## Verdict
Adopt: per-persona scheme catalogs with superset-plus-swap composition; fingerprint personas by scheme md5 instead of classpath archaeology. Adapt the persona taxonomy. Omit JetBrains' promo-group mechanics unless porting their edition model.
