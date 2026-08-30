<!-- capsule-v2 -->
# FCR grammar kernel — what is the exact planner-output grammar every applier consumes, and how does parsing degrade when the model deviates?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** Every planner emits `<modify file="...">...</modify>`-style blocks and every applier (fcr-application-loop, fcr-prevalidation-plane, search-replace-match-ladder) consumes parsed FileChangeRequests — what is the exact grammar, where does parsing normalize model slop, and what happens when a block does not match at all?

## RegexMatchableBaseModel + FileChangeRequest._regex: one backreferenced tag grammar, fixed attribute order, groupdict construction
**Path/Symbol:** `sweepai/core/entities.py:RegexMatchableBaseModel` (:73–87), `RegexMatchError` (:69), `FileChangeRequest` (:117–162), `_regex` (:130), `from_string` override (:164–184), `relevant_files` property (:186–194), `parse_fcr` (:507–523), `render_fcrs` (:526+); sibling grammars `SweepPullRequest._regex` (:275), `ProposedIssue._regex` (:282). **Consumers of parse_fcr:** `sweepai/agents/modify.py:47`, `sweepai/agents/modify_utils.py:789/:1298/:1318`, `entities.py:530` (render_fcrs). **COPIED_FROM markers:** taught at `sweepai/core/prompts.py:250/:253`, consumed at `sweepai/core/sweep_bot.py:681–684` (live), `:997–1000` (context variant), `:1533–1535` (GHA variant, create-type only).

**Signature:** `FileChangeRequest.from_string(string: str, **kwargs) -> FileChangeRequest` (raises `RegexMatchError("Did not match")` on no match); `parse_fcr(fcr) -> dict` with keys justification/file_path/original_code/new_code/replace_all.
**Data Shape:** the wire format is XML-ish tags: opening `<{change_type} file="..." [start_line=".."] [end_line=".."] [entity=".."] [source_file=".."] [destination_module=".."] [relevant_files=".."]>` with instructions as body up to `</{change_type}>`; change_type ∈ {modify, create, delete, rename, rewrite, check, refactor, test} (pydantic Literal enforced AFTER regex capture, which accepts any `[a-z_]+`).

### Decisive source
```python
class RegexMatchableBaseModel(BaseModel):
    _regex: ClassVar[str]
    @classmethod
    def from_string(cls, string: str, **kwargs) -> Self:
        match = re.search(cls._regex, string, re.DOTALL)
        if match is None:
            logger.warning(f"Did not match {string} with pattern {cls._regex}")
            raise RegexMatchError("Did not match")
        return cls(**{k: (v if v else "").strip("\n") for k, v in match.groupdict().items()}, **kwargs)

# FileChangeRequest._regex (abridged to the load-bearing parts):
r"""<(?P<change_type>[a-z_]+)\s+file=\"(?P<filename>[a-zA-Z0-9/\\\.\[\]\(\)\_\+\- @\{\}]*?)\"( start_line=\"(?P<start_line>.*?)\")?( end_line=\"(?P<end_line>.*?)\")?( entity=\"(.*?)\")?( source_file=\"(?P<source_file>.*?)\")?( destination_module=\"(?P<destination_module>.*?)\")?( relevant_files=\"(?P<raw_relevant_files>.*?)\")?(.*?)>(?P<instructions>.*?)\s*</\1>"""

# from_string override — model-slop normalization:
result.filename = result.filename.strip("/")
result.instructions = result.instructions.replace("\n*", "\n•")
if " " in result.source_file: result.source_file = result.source_file.split(" ")[0]
if result.start_line:
    try: result.start_line = int(result.start_line)
    except ValueError: result.start_line = None
if result.end_line:
    try: result.end_line = int(result.end_line)
    except ValueError: result.start_line = None      # BUG AT PIN: assigns start_line, not end_line (:183)

# parse_fcr — the inner code-block grammar:
justification, *_ = fcr.instructions.split("<original_code>", 1)
justification, *_ = justification.split("<new_code>", 1)
justification = justification.rstrip().removesuffix("1.").removesuffix("2.").rstrip()  # sometimes Claude puts 1. <original_code>
original_code_pattern = r"<original_code(?: file_path=\".*?\")?(?: index=\"\d+\")?>\s*\n(.*?)</original_code>"
replace_all_pattern = r"<replace_all>true</replace_all>"
```

**Flow:** from_string is a single `re.search(..., re.DOTALL)` against the class-level `_regex`; NO match ⇒ warning log + `RegexMatchError` (the planner variants catch it and return `([], "")` — see gha-planning-variant-body / llm-plan-continuation-and-repair); a match builds the pydantic model straight from `match.groupdict()` with empty captures coerced to "" and newlines stripped — so OPTIONAL attributes that the model omitted become empty strings, and the Literal validation of change_type runs at construction (a block tagged `<fix ...>` parses the regex fine but then fails pydantic). The backreference `</>` forces the closing tag to repeat the opening tag name — mismatched close tags simply do not match. The filename character class is CLOSED (letters/digits/slash/backslash/dot/brackets/parens/underscore/plus/hyphen/space/@/braces — no quotes or angle brackets), so a filename containing a quote silently truncates the match. The from_string override then normalizes model slop: leading/trailing slashes off filenames, markdown bullets ("
*" and leading "*") rewritten to "•", multi-token source_file truncated to its first token, start/end lines int-coerced with ValueError ⇒ None — including the pin bug where a bad end_line clears START_line instead. parse_fcr then reads the INNER grammar out of instructions: justification is whatever precedes the first `<original_code>` (itself cut at `<new_code>`), with trailing list-number artifacts ("1."/"2.") removed; original/new code blocks are finditer-extracted with patterns that TOLERATE optional `file_path="..."` and `index="\d+"` attributes on the tags (the repair prompt's index-addressed grammar reuses these same tags); bodies pass through strip_triple_quotes (fence stripping); replace_all is the mere presence of literal `<replace_all>true</replace_all>`. COPIED_FROM_PREVIOUS_MODIFY is a grammar-level escape hatch: the repair prompt teaches the model to enter the marker verbatim into a modify block, and the repair loops then override ONLY the filename (live/context variants through renames_dict; GHA variant directly, create-type only) while keeping the previous FCR's code blocks — large code never has to be re-transmitted through the repair model.
**Invariant:** The tag name IS the change type and the closing tag must echo it (`` backreference) — a port that decouples them loses the free consistency check. Attribute ORDER in the regex is fixed (start_line, end_line, entity, source_file, destination_module, relevant_files); the model emitting them in another order does not match. Empty-capture→"" means "attribute absent" and "attribute present but empty" are indistinguishable downstream. parse_fcr's dict shape (justification + parallel original_code/new_code LISTS + replace_all bool) is the contract the whole application plane consumes — multiple original_code blocks per FCR are legal (list), and a FCR with zero new_code blocks renders as plain-instructions in render_fcrs. The COPIED_FROM markers are matched by substring INSTRUCTIONS containment, not by any structured field — they are prompt-contract tokens, and the marker text lives in prompts.py, not in the parser.
**Probe:** No offline-runnable test covers this kernel at pin (tests/ holds live-API harness scripts; tests/modify_tests/ references none of these symbols — grep confirmed zero hits). Deterministic probes executed at pin: `grep -n '_regex = ' sweepai/core/entities.py` → :130,:275,:282 (three grammars); `grep -n 'result.start_line = None' sweepai/core/entities.py` → :178,:183 (two rows — the second is the end_line-branch bug); `grep -rn 'COPIED_FROM_PREVIOUS_MODIFY' sweepai --include=*.py` → 4 rows (sweep_bot.py:681,:997 live checks + prompts.py:250,:253 teaching); `grep -rn 'COPIED_FROM_PREVIOUS_CREATE' sweepai --include=*.py` → 4 rows (sweep_bot.py:1533 live check + :682/:998/:1534 comments); `grep -n 'def parse_fcr\|def render_fcrs' sweepai/core/entities.py` → :507,:526; `grep -rn 'parse_fcr(' sweepai --include=*.py | grep -v def` → modify.py:47, modify_utils.py:789/:1298/:1318, entities.py:530.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "FileChangeRequest _regex from_string RegexMatchError parse_fcr COPIED_FROM_PREVIOUS_MODIFY", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// entities.py :69-194/:507-545 + prompts.py:240-262 + sweep_bot.py:665-705/:1528-1540 at pin
// substituted — see verification.md pass 7.
```

## Verdict
Adopt the single-regex-per-entity pattern with a class-level `_regex` ClassVar + shared from_string (one parsing path for every consumer, fail-loud RegexMatchError that planners convert to safe-empty results), the closing-tag backreference as a free consistency check, the empty-capture→"" normalization, and the COPIED_FROM substring markers as a cheap way to keep large payloads out of repair-model context. Adapt: the closed filename character class will reject legitimate paths (spaces work, quotes do not) — widen it deliberately; the fixed attribute order is brittle to model output — consider an attribute-bag regex if your planner model reorders; the end_line/start_line coercion bug (:183) should NOT be ported; the Literal-after-regex split means unknown tag names surface as pydantic errors rather than RegexMatchError — unify if you want one failure type. Omit: the sibling SweepPullRequest/ProposedIssue grammars (product-specific), and the "1."/"2." removesuffix hack unless your model actually numbers blocks. Coverage caveat: no direct test at pin; this kernel sits under EVERY planner and applier capsule in this leaf, so a grammar change here invalidates all of them at once.
