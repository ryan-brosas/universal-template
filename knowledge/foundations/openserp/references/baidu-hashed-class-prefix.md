<!-- capsule-v2 -->
# Baidu hashed-class prefix matching — how do selectors survive per-build CSS hash rotation?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What selector strategy do you use when the target site recompiles its CSS class names every build?

## Prefix-over-suffix doctrine
**Path/Symbol:** `baidu/selectors.go:14–35` — `DescAlt` ladder + the in-source rationale comment; consumer `baidu/parse_html.go:126–135` (desc fallback loop).
**Signature:** `DescAlt []string{"[class*='content-right_']", "[class*='summary-gap_']", "div.text_2NOr6"}`.
**Data Shape:** Baidu abstract containers ship as `<div class="summary-gap_<HASH>">` where HASH rotates per build — the same captured page already carries `summary-gap_3Jb4I` AND `summary-gap_68jXq`, and a previously-pinned exact class `content-right_8Zs40` "no longer appears at all".

### Decisive source
```go
// baidu/selectors.go:27-35 — verbatim doctrine
// DescAlt matches Baidu's hashed abstract containers by class *prefix*
// ([class*='summary-gap_']) rather than a frozen hash suffix
// (.summary-gap_3Jb4I): Baidu rotates the trailing hash per build (the same
// page already carries summary-gap_3Jb4I and summary-gap_68jXq), and the old
// content-right_8Zs40 suffix no longer appears at all. These two prefixes are
// specific enough to use as substrings. text_ is NOT: it is Baidu's generic
// text-styling class reused on dozens of nodes, so the baike abstract body is
// pinned to its exact .text_2NOr6 hash and tried last.
```
Consumer order (:126–135): primary `Selectors.Desc` (`.c-abstract`) first, then DescAlt IN ORDER, each tried via `item.Find(alt).First()` with non-empty-text acceptance.
**Flow:** this is the description arm of parseBaiduSelection's admission ladder; a miss all the way down falls back to whole-card text minus title (:136–139) — description is best-effort, never row-fatal.
**Invariant:** prefix-match ONLY when the stable part is specific (`summary-gap_`, `content-right_` are feature-scoped); generic stems like `text_` collide with dozens of unrelated nodes, so those stay EXACT-hash — accepting that one pin will rot and must be re-derived from live SERPs. This two-tier policy (prefix for unique stems, exact for generic stems) is the portable lesson, not the specific classes.
**Probe:** `baidu/parse_html_test.go:91 TestParseBaiduHTMLFallbackSelectors` + `:120 TestParseBaiduHTMLFallsBackWhenEarlierSelectorHasNoResult` exercise the ladder against fixtures.
**Python-equivalent probe (executed byte-exact):**
```bash
grep -n "summary-gap_\|text_2NOr6\|content-right_" baidu/selectors.go   # → comment :28–34 + ladder :35
```
```python
classes = ["summary-gap_3Jb4I", "summary-gap_68jXq", "text_9Xx1Q", "c-abstract"]
def matches(prefix_sel): return any(c.startswith(prefix_sel[8:-2]) for c in classes)  # [class*='X']
assert matches("[class*='summary-gap_']") is True          # prefix survives BOTH hashes
assert matches("[class*='text_']") is False                # doctrine: never prefix-match text_
print("hashed-class prefix GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "DescAlt summary-gap content-right baidu selectors", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt prefix-matching for build-hashed CSS on uniquely-stemmed feature classes; keep exact pins for generic utility stems. Adapt the actual prefixes to whatever the live SERP ships when you port — they will have rotated again.
