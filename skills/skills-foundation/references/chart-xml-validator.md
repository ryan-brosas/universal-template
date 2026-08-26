<!-- capsule-v2 -->
# Chart XML Validator — which schema-legal chart XML does PowerPoint still refuse, and why does the validator detect rather than repair?

**Source:** anthropics/skills (office/helpers/pptx_chart.py, byte-identical in pptx/docx/xlsx skills; source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What are the two failure classes that pass ISO-29500 validation but get a chart discarded or refused at open?

## Stacked dLblPos + unresolved axId checks
**Path/Symbol:** `skills/pptx/scripts/office/helpers/pptx_chart.py` (`find_chart_problems` :164–170 entry; `_check_stacked_label_positions` :41–60; `STACKED_GROUPINGS`/`ILLEGAL_ON_STACKED`/`LEGAL_ON_STACKED` :27–29; `_check_chart_axis_references` :117–152; `AXID_MINIMUM` :37–45; `_ext_lst_spans` depth-matched stripper :154–170; `_CHART_PART_RE` selects only `ppt/charts/chartN.xml`).
**Signature:** `find_chart_problems(files: Mapping[str, bytes]) -> list[str]` — takes the UNPACKED package as a name→bytes map.
**Data Shape:** problem strings prefixed by part path; two classes: (1) `<c:dLblPos val="outEnd"/>` inside a `grouping="stacked|percentStacked"` bar/bar3D group (only ctr/inEnd/inBase legal); (2) a `<c:NNChart>` group whose `<c:axId>` refs don't resolve to ≥2 axes declared in the same part (3 minimum for line3D/surface3D per AXID_MINIMUM).

### Decisive source
```python
STACKED_GROUPINGS = frozenset({"stacked", "percentStacked"})
ILLEGAL_ON_STACKED = frozenset({"outEnd"})
LEGAL_ON_STACKED = ("ctr", "inEnd", "inBase")
```
```python
problems.append(
    f"{part}: <c:{kind}> references axId {', '.join(ids)}, {detail}, "
    f"leaving fewer than two live axes; PowerPoint discards the chart. {hint}")
```

**Flow:** for each chart part → strip `<c:extLst>` spans (depth-counted so nested extLst can't confuse the regex sweep) → scan every chart-group block: stacked grouping? flag outEnd dLblPos with count + legal vocabulary → collect declared axes from catAx/dateAx/valAx/serAx elements → any chart group referencing undeclared/no axes gets class-specific Fix hints (point at canonical ids when exactly 1 cat+1 val declared; else declare-or-drop advice).
**Invariant:** Detection ONLY — the module docstring states it outright: both faults have multiple valid repairs and "only the author knows which was meant". The validator never mutates XML. extLst stripping exists because extension blocks legally re-declare elements that would false-positive the label check. This is the machine-checkable half of the corruption ladder capsule (generation rules there, post-hoc detection here).
**Probe:** No unit tests upstream. Deterministic probe: feed find_chart_problems an unpacked deck map containing a stacked-bar chart with `dLblPos="outEnd"` → expect the refusal message naming the three legal positions; feed a chart whose axIds reference nothing → expect the discard warning.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "find_chart_problems dLblPos stacked", limit: 5 });
```

## Verdict
Adopt verbatim as a post-edit gate in any OOXML pipeline that touches charts — run it after every XML mutation, before rezip. Adapt nothing behavioral. Omit the XSD corpora it complements. Caveat: pinned by whole-file read + triple-copy md5 identity, no direct tests.
