<!-- capsule-v2 -->
# FUS events-scheme.json grammar — how does JetBrains ship its whole telemetry validation schema as one data file?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What file grammar lets a vendor validate every analytics event field-by-field WITHOUT shipping validation code — so a porter can emit conforming telemetry or port the schema-driven validator pattern?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.pycharm.community.jar:event-log-metadata/FUS/events-scheme.json` (979,376 bytes, `"version":"7613"`); sibling schemes per family under `event-log-metadata/<FAMILY>/events-scheme.json` (11 families, see event-log-metadata-family-layout).
**Signature:** top level `{groups:[], rules:{enums:{},regexps:{}}, version:"N"}` — `version` is a monotonically increasing SCHEMA revision counter (7613 py @ PY-262.9437.214), not a build number.
**Data Shape:** each group = `{id, builds:[], versions:[{from[,to]}], rules}` where `rules.event_id` is a list of validators for the event name and `rules.event_data` maps field-name → LIST of acceptable validators (union semantics). Validator forms seen in FUS v7613 (occurrence-exact): `{enum:A|B|C}` inline closed vocabulary ×2467, `{regexp#name}` ref into top-level named regexps ×2147, `{enum#name}` ref into shared enum tables ×1755, `{util#Name}` ref into CODE-RESIDENT util validators ×955, `{dictionary#file.ndjson}` ref into shipped whitelist dictionaries ×7, `{default_value:val|category|bucket}` ×8. Literal strings also appear as bare list items. `rules.enums` (278 group-local blocks) define reusable vocabularies whose conventional first key is `__event_id`.

### Decisive source
```json
{"id": "accessibility", "builds": [], "versions": [{"from": "1"}],
 "rules": {"event_id": [
   "{enum:screen.reader.detected|screen.reader.support.enabled|screen.reader.support.enabled.in.vmoptions|linux.accessibility.support.enabled}"]}}
```
and the union-list form (find.usages `searchScope` field, truncated):
```json
"searchScope":["{enum:All_Places|Project_Files|…|Current_File]}", "{util#scopeRule}",
 "{enum:Current File}", "{default_value:third.party|options|4}"]
```
and the nested event_data form (`accessibility.state`): `"event_data":{"enabled":["{enum#boolean}"]}`.

**Flow:** instrumentation code logs `(groupId, eventId, fields)` → runtime validator resolves the group by id → checks version applicability (`versions[].from` upward, `to` optional; 590/716 groups are from:"1", zero multi-version ranges shipped, zero non-empty `builds`) → each field passes if it matches ANY validator in its list → undeclared fields/values drop at validation (complements the deny-by-default collector catalog of fus-collector-registration).
**Invariant:** the scheme file IS the privacy+compat contract: a value not covered by some validator is dropped, so extending telemetry = editing DATA, not code. The three reference namespaces have different lifecycles — `enum:` inline is frozen per-group, `enum#`/`regexp#` resolve within the SAME file, but `{util#X}` and `{default_value:…}` point at code-side behavior NOT shipped in any JSON — a porter must reimplement those 963 validator sites or accept their loss.
**Probe:** from `<install>` root:
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '"event_id"' | wc -l` → `716`;
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '{util#' | wc -l` → `955`.
**Coverage caveat:** jar resource plane — invisible to the graph (BM25 search_graph returns only wrong-plane jupyter-web hits for EventsSchemeBuilder; search_code finds zero because jar contents aren't text-indexed); unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no graph target for this plane (adjudicated per mcp-spec/jb precedent). Deterministic retrieval is:
`unzip -l lib/intellij.pycharm.community.jar | grep 'event-log-metadata/[A-Z_]*/events-scheme.json$'` → exactly 11 rows; the validator CODE side lives as class names in `lib/intellij.platform.statistics.jar` (`com/intellij/internal/statistic/eventLog/events/scheme/{EventsSchemeBuilder,EventSchemeValidator,EventDescriptor}.class`, `unzip -l` name-level evidence only).

**Complements:** fus-telemetry-metadata-plane (pass 2) owns the DICTIONARY whitelists; fus-collector-registration owns collector registration. This capsule owns the scheme FILE grammar itself.

## Verdict
Adopt: schema-versioned, union-of-validators event contracts as data; the `{kind:value}` micro-grammar composes enums/regexps/dictionaries/util-code/default-fallbacks in ONE field spec. Adapt the validator kinds to your host. Omit JetBrains' util-validator implementations (not shipped as source anywhere in these installs).
