<!-- capsule-v2 -->
# Test-editing variant plane — how do you plan a TEST-WRITING pass over already-modified files, and how much of that variant is actually alive?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What does the test-writing planner do differently from the live issue-fixing planner — snippet partition inversion, post-change content swap, diff framing, single-shot continuation — and is any of it reachable at pin?

## get_files_to_change_for_test: inverted partition + content swap + diff message + one-shot continuation (DEAD at pin)
**Path/Symbol:** `sweepai/core/sweep_bot.py:get_files_to_change_for_test` (:1158–1357); helpers `get_max_snippets` (:346–364), `generate_diff` (`sweepai/utils/diff.py:9–33`), `get_annotated_source_code` (`sweepai/core/annotate_code_openai.py:96–135`, see snippet-annotation-plane); prompts `sweepai/core/prompts.py:test_files_to_change_system_prompt` (:264) / `test_files_to_change_prompt` (:278); model routing `sweepai/core/chat.py:chat_anthropic` (:354–379). **Caller audit: ZERO callers at pin** — whole-repo grep finds only the definition; this is a planned-but-unwired variant of the live `get_files_to_change` (:398).
**Signature:** `get_files_to_change_for_test(relevant_snippets, read_only_snippets, problem_statement, updated_files: dict[str, dict[str, str]], cloned_repo, import_graph=None, chat_logger=None) -> tuple[list[FileChangeRequest], str]`.
**Data Shape:** input = ranked Snippet lists PLUS `updated_files` mapping path → {"original_contents", "contents"} (the fix already applied); output = FCR list for NEW/UPDATED TESTS + raw plan string; failure shape = `([], "")` on RegexMatchError.

### Decisive source
```python
# INVERSION vs the live planner: "test" paths become RELEVANT, everything else read-only
for snippet in relevant_snippets + read_only_snippets:
    if snippet in new_relevant_snippets or snippet in new_read_only_snippets:
        continue
    if "test" in snippet.file_path:
        new_relevant_snippets.append(snippet)
    else:
        new_read_only_snippets.append(snippet)

# CONTENT SWAP: the LLM sees POST-change code, not the pre-fix snippets
for relevant_snippet in relevant_snippets:
    if relevant_snippet.file_path in updated_files:
        relevant_snippet.content = updated_files[relevant_snippet.file_path]["contents"]

# the fix itself is framed as context to be tested
diff_string += f"```diff\n{file_path}\n{generate_diff(file_info['original_contents'], file_info['contents'], n=10)}\n```"
content=f"# Here are the changes we have made to resolve the issue that needs testing:\n<diff>\n{diff_string}\n</diff>\n",

# ONE-SHOT continuation: length over ~12.9k chars AND no closing </plan> tag ⇒ exactly one empty-content follow-up
max_tokens = 4096 * 3.5 * 0.9 # approx max tokens per response
expected_plan_count = 1
call_anthropic_second_time = len(files_to_change_response) > max_tokens and files_to_change_response.count("</plan>") < expected_plan_count
if call_anthropic_second_time:
    second_response = chat_gpt.chat_anthropic(content="", model=MODEL, temperature=0.1)  # content="" ⇒ no new user message appended (chat.py:380)
    files_to_change_response += second_response
```

**Flow:** (unreachable at pin) caller would pass the post-fix snippet lists + updated_files → dedup loop over relevant+read_only re-partitions by substring "test" with the LIVE variant's direction INVERTED (test→relevant, non-test→read_only; live get_files_to_change :426–432 sends test→read_only) → both lists' snippet.content swapped to updated_files[path]["contents"] → interleave → get_max_snippets (shared budget kernel, see llm-file-selection-budget-plane) → unconditional [::-1] reverse (:1204, no dead-flag wrapper here) → re-split by file_path membership → render: read_only plain via its own `<read_only_snippet>` template; relevant via get_annotated_source_code under `if True:` (:1227) with an expand(300) else-branch → `<issue>` block → ```diff blocks over ALL updated_files (generate_diff n=10) framed as "changes we have made … that needs testing" → optional reverse import-graph message ("The file 'X' is imported by the following files", .venv/build skipped) → ONE chat_anthropic call (MODEL="claude-3-opus-20240229", temperature 0.1, NO use_openai arg ⇒ default False, but chat.py:369–370 flips to gpt-4o when ANTHROPIC_API_KEY is unset and not ANTHROPIC_AVAILABLE — the pin runs only when an Anthropic key exists) → one-shot continuation gate (len > 4096*3.5*0.9 AND count("</plan") < 1 ⇒ one empty-content follow-up, concatenated; failure logged, partial kept) → chat_logger.add_chat records model=MODEL even when gpt-4o actually ran → parse `<relevant_modules>` DOTALL tag (stamped as raw_relevant_files on every FCR) + FileChangeRequest._regex finditer → return (fcrs, response); RegexMatchError → ([], ""). No renames step, no sub-request step, no continuous_llm_calls loop, no repair rounds.
**Invariant:** The variant's whole contract is "plan tests against POST-change code": the content swap must happen BEFORE rendering or the model plans against stale pre-fix code, and the diff message must carry original→new so the model knows what changed. The continuation gate is keyed on the ABSENCE of the closing `</plan>` tag combined with a length threshold — a truncated plan without its end tag triggers exactly ONE retry, never a loop (contrast continuous_llm_calls' MAX_CALLS=10). The env-dependent model routing means the recorded model name (and the chat_logger ledger entry) can disagree with the model that actually ran — a port that logs model identity must log the RESOLVED model, not the requested one. generate_diff's old_lines/new_lines variables and default_kwargs {"n": 5} are dead code (diff.py:14–26): the real diff runs on stripped inputs, so leading/trailing blank lines never appear in the diff, and n works only because callers pass it through kwargs.
**Probe:** No offline-runnable test exists for sweep_bot at pin (standing finding). Deterministic probes executed at pin: `grep -rn 'get_files_to_change_for_test' <repo>` (whole checkout incl. tests/) → exactly 1 row, the def at sweep_bot.py:1158 (ZERO callers — dead at pin); `grep -n '"test" in snippet.file_path' sweepai/core/sweep_bot.py` → :368,:426,:734,:1179 (four sites: partition helper, live planner, for_gha twin, for_test inversion); `grep -n 'updated_files\[.*file_path\]\["contents"\]' sweepai/core/sweep_bot.py` → :1189,:1193 (for_test) + :1379,:1383 (for_gha twin) + :213 (helper); `grep -n "generate_diff(file_info" sweepai/core/sweep_bot.py` → :1269 only (n=10); `grep -n 'import_graph.reverse()' sweepai/core/sweep_bot.py` → :1089,:1280; `grep -n '4096 \* 3.5 \* 0.9' sweepai/core/sweep_bot.py` → :1317 only; `grep -n 'expected_plan_count' sweepai/core/sweep_bot.py` → :1318,:1319; `grep -n 'default_kwargs' sweepai/utils/diff.py` → :25,:26 (computed, never referenced); `grep -n 'raw_relevant_files = " ".join(relevant_modules)' sweepai/core/sweep_bot.py` → :641,:957,:1351,:1506 (all four plan variants stamp it identically).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get_files_to_change_for_test updated_files generate_diff relevant_modules plan continuation", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// sweep_bot.py:1158-1357/:366-395, utils/diff.py:9-33, prompts.py:264-290, chat.py:354-380 at pin
// substituted — see verification.md pass 5.
```

## Verdict
Adopt the three transferable mechanics even though the function is dead at pin: (1) the INVERTED partition for a test-writing pass (tests become the primary reference, production code becomes read-only context); (2) the pre-render CONTENT SWAP from an updated_files map so the planner sees post-change code plus an explicit original→new diff framed as "what needs testing"; (3) the one-shot continuation gate keyed on missing closing tag + length threshold — cheaper than a full retry loop for a single expected `<plan>` block. Adapt: resolve and LOG the actual model used (the source logs the requested pin while gpt-4o may run); give the dead variant a real caller or delete it (dead planning code drifts from the live planner's repair ladder). Omit: the substring-"test" partition (same false-positive class as the live variant — drops/matches non-test files like latest.py), the msg-style print debug dumps, and generate_diff's dead line bookkeeping. Coverage caveat: zero callers at pin means no behavioral test can exist; every claim here is source-confirmed but behavior-unverified.
