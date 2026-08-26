<!-- capsule-v2 -->
# Google adapter — which selector ladder survives headless vs headful SERP divergence, and how are virtualized image grids harvested?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the web parser filter non-result blocks from the broad fallback selector, and why must image cells be right-clicked and removed?

## Web: canonical-first, broad-with-filter
**Path/Symbol:** `google/selectors.go:Results` ("div.tF2Cxc:not(:has(div.tF2Cxc))"), `google/search.go:Search` (L228–492), `preparePage/waitAnswersExpanded/googleElementHasAdMarker`.
**Signature:** `WaitForElements(ctx, page, []string{Selectors.Results, Selectors.ResultsBroad}, timeout) (rod.Elements, matchedSelector, err)`.
**Data Shape:** matchedOrganic ⇔ matchedSelector == Selectors.Results.

### Decisive source
```go
matchedOrganic := matchedSelector == Selectors.Results
...
} else if isResultCandidate {          // broad fallback ALSO matches knowledge panels/nav
	isResultCandidate := matchedOrganic || core.HasAttribute(resEl, "data-ved")
...
// description ladder: DescPrimary → DescFallback → structural:
anchor := titleTag
for i := 0; i < 3 && anchor != nil; i++ { anchor, err = anchor.Parent() }
if sib, err := anchor.Next(); err == nil { ... DescAny ... }
// PAA expansion poll (replaces flat 2s sleep):
for { text,_ := answers[0].Text(); if len(strings.Split(text,"\n")) >= 2 { break }; ...100ms... }
// answer slice guard against len==2 panic:
descEnd := max(len(answerText)-2, 1)
```
`preparePage` deletes `div[data-initq]` (similar-queries lists) BEFORE parsing so PAA specs don't double-count.

## Images: interact-to-materialize + O(n) removal
**Path/Symbol:** `google/search.go:SearchImage/parseImageCell` (L496–636).
**Data Shape:** map keyed by data-ved; maxImagePasses=20; stagnant≥2 breaks.

### Decisive source
```go
// Right-clicking forces the cell to materialize its imgres link (grid is
// virtualized; href absent until interaction):
if err := r.Click(proto.InputMouseButtonRight, 1); err != nil { return }
...
if err := r.Remove(); err != nil { ... }   // ALWAYS remove parsed cells:
// without this we re-iterate already-parsed cells → O(n²) or hang when
// right-click on a stale node never returns.
```

**Flow:** BuildURL (gl/hl/uule/pws=0/sourceid=chrome) → Navigate → preparePage → classifyPage → acceptCookies ONLY when features requested → WaitForElements → rank := NewRankStateAt(Start, Start+1) → per-element branch ad / answer-box / candidate → DeduplicateResults → zero ⇒ re-classify (ErrEmptyResult ⇒ nil,nil; elems>0 ⇒ ErrSearchTimeout) → AttachFeaturesToFirstResult.
**Invariant:** ads detected via element Matches OR child `[data-text-ad]`; broad-selector candidates require data-ved else they'd inject nav/knowledge junk; image Description packs "Height:%v, Width:%v, Source Page: %v" — the contract parseImageDescription later regex-parses.
**Probe:** `go test ./google -run TestGoogleParseHTMLFixtures`; integration tests skipped without `-tags=integration`.
**Probe executed (real runner):** same command at pin = **1 top-level PASS** covering all five fixture files as subtests (results/no-results/captcha/captcha_new/soft_block); sibling TestGoogleClassifyRawHTML = 1 PASS; live SERP integration remains tag-gated off by design.
**Python-equivalent probe (executed):**
```bash
grep -c 'data-ved\|tF2Cxc' google/selectors.go google/search.go google/search_raw.go  # → 3/7/4: both paths reference the same anchors
grep -n 'maxImagePasses\|r.Remove()' google/search.go | head -4
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "parseImageCell waitAnswersExpanded searchResultSelectors ResultsBroad data-ved", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt canonical-innermost-first with attribute-guarded fallback, the PAA poll, and the remove-after-parse image pattern; adapt the class names (they rotate with Google DOM); omit image search unless you accept the right-click hack's fragility.
