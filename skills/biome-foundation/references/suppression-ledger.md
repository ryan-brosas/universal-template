<!-- capsule-v2 -->
# Suppression ledger — how do line/top-level/range suppressions stay position-ordered and honest about being unused?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a linter must honor `ignore` / `ignore-all` / `ignore-start/end` comments, flag unused and unknown ones, and match signals against them cheaply — what data structure makes the matching O(log n) and the honesty checks possible?

## The Suppressions seam
**Path/Symbol:** `crates/biome_analyze/src/suppressions.rs` — `Suppressions` (:417-427), `LineSuppression` (:120-145), `TopLevelSuppression` (:16-31), `RangeSuppression` (:178-205), `push_suppression` (:541-577), `overlap_last_suppression` (:600-631), `expand_range` (:579-593), `overlapping_line_suppressions` (:657-687), `already_suppressed` (:635-648), `finalize` (:652-655).
**Signature:** `fn overlapping_line_suppressions(&mut self, target: &TextRange) -> &mut [LineSuppression]`; `fn push_suppression(&mut self, suppression: &AnalyzerSuppression, comment_range: TextRange, is_leading_in_file: bool) -> Result<(), AnalyzerSuppressionDiagnostic>`.
**Data Shape:** three parallel ledgers: `line_suppressions: Vec<LineSuppression>` (kept sorted by construction — pushed in traversal order), `top_level_suppression: TopLevelSuppression` (single slot; `filters_by_category: FxHashMap<RuleCategory, FxHashSet<RuleFilter<'static>>>`), `range_suppressions: Vec<RangeSuppression>` (stack discipline: start pushes, end marks `is_ended`).

### Decisive source
```rust
// suppressions.rs:657-686 — binary_search + linear walk to BOTH sides (comment-pinned perf trade):
let Ok(middle_index) = self.line_suppressions.binary_search_by(|s| {
    if s.text_range.end() < target.start() { Ordering::Less }
    else if target.end() < s.text_range.start() { Ordering::Greater }
    else { Ordering::Equal }
}) else { return &mut []; };
// Perf: normally just traversing in both directions should be faster - more than 2
// comments in a row should be rare, and 2-3 extra comparisons are faster than
// bisecting twice for left and right border.
```
```rust
// suppressions.rs:608-618 — a line comment extends FORWARD onto the next line,
// walking the tail of consecutive same-line entries:
if last_suppression.line_index == next_line_index
    || last_suppression.line_index + 1 == next_line_index
{
    last_suppression.line_index = next_line_index;
    last_suppression.text_range = last_suppression.text_range.cover(text_range);
}
```
**Flow:** `handle_comment` → `parse_suppression_comment` results → `<explanation>` placeholder rejected as `suppressions/incorrect` (lib.rs:532-541) → `map_to_rule_filter` validates rule/group names against `MetadataRegistry`, unknown names become `suppressions/unknownRule`/`unknownGroup` errors (assists get distinct wording) (:480-523) → dispatch by variant: Line pushes a `LineSuppression` seeded with `text_range = comment_span`; TopLevel requires `is_leading_in_file` or errors "Top level suppressions can only be used at the beginning of the file" (:54-69); RangeStart pushes an open `RangeSuppression`, RangeEnd finds the LAST open entry whose filters match and closes it covering its own range, unmatched end ⇒ error (:266-324). Before pushing, `already_suppressed` records whether top-level/range already covers this filter so the later "no effect because another suppression" note can point at the winning comment (:551, :635-648). Range-end without start and unterminated starts at `finalize()` both produce diagnostics (:267-276, :397-413).
**Invariant:** line-suppression ranges only ever GROW (`cover`) and grow by exactly one line forward per comment; binary search over `line_suppressions` is valid because insertion order is token order; `did_suppress_signal` flips on every consuming match so unused ones can be reported after all phases; instance suppressions (`RuleInstance(rule, instance)`) suppress ONE call-site instance and must not mark exhaustive.
**Probe:** `crates/biome_analyze/src/matcher.rs` tests :201-380 build trees with `//group`, `//group/rule`, `//unknown_group`, `//group/unknown_rule` comments and assert exact diagnostic order ending in `suppressions/unused`; lib.rs post-run loops :195-243 emit "Suppression comment has no effect..." for every non-hitting entry.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Suppressions push_suppression map_to_rule_filter overlap_last_suppression", limit: 10, fields: ["signature", "name", "file"] });
// map_to_rule_filter suppressions.rs 480-523; TopLevelSuppression.push_suppression 47-78; RangeSuppressions.push_suppression 233-326 (line-exact)
```

## Verdict
Adopt the three-ledger split (per-line vec + single top-level + range stack), sorted-by-construction binary search with linear edge walks, forward line extension, and unused/unknown/duplicate honesty reporting; adapt comment grammar per language; omit plugin-name subcategory plumbing unless porting plugins. Coverage caveat: pinned via matcher.rs order tests + upstream biome_suppression unit suites; no dedicated integration test for the range-stack pairing matrix beyond finalize().
