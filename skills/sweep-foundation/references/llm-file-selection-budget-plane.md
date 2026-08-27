<!-- capsule-v2 -->
# LLM file-selection budget plane — how do you budget, order, and parse an LLM file-selection response so a bad answer can never empty the context?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What is the full pipeline from ranked snippets to the two file-path lists the ticket context is rebuilt from — interleaving, test partition, char-budget walk, ordering reversal, XML prompt assembly, model routing, and filename-shape parsing — and which of its guards are load-bearing?

## context_get_files_to_change: interleave → partition → budget-walk → reverse → XML prompt → shape-parse
**Path/Symbol:** `sweepai/core/sweep_bot.py:context_get_files_to_change` (:1021–1156), `get_max_snippets` (:346–364), `partition_snippets_if_test` (:366–369), `parse_filenames` (:181–191); constants `SNIPPET_TOKEN_BUDGET = int(150_000 * 3.5)` (:62), `MAX_SNIPPETS = 15` (:63); single production caller `sweepai/utils/ticket_utils.py:get_relevant_context` (:443–502, call at :460); model override `sweepai/core/chat.py:chat_anthropic` (:354–379).
**Signature:** `context_get_files_to_change(relevant_snippets, read_only_snippets, problem_statement, repo_name, cloned_repo, import_graph=None, pr_diffs="", chat_logger=None, seed=0, images=None) -> tuple[list[str], list[str]]` (relevant paths, read-only paths).
**Data Shape:** input = ranked `Snippet` lists (file_path/start/end/content/type_name); output = deduped repo-relative path strings; the caller rebuilds each path as a WHOLE-FILE snippet (`start=0, end=len(content.split("\n"))`).

### Decisive source
```python
# interleave relevant[i]/read_only[i], drop every "test"-substring path, budget-walk, then REVERSE under a dead flag
interleaved_snippets = partition_snippets_if_test(interleaved_snippets, include_tests=False)
max_snippets = get_max_snippets(interleaved_snippets)
if True:
    max_snippets = max_snippets[::-1]
relevant_snippets = [snippet for snippet in max_snippets if any(snippet.file_path == relevant_snippet.file_path for relevant_snippet in relevant_snippets)]
read_only_snippets = [snippet for snippet in max_snippets if not any(snippet.file_path == relevant_snippet.file_path for relevant_snippet in relevant_snippets)]

# get_max_snippets — walk DOWN from min(len, MAX_SNIPPETS=15), return the FIRST prefix that fits
START_INDEX = min(len(snippets), MAX_SNIPPETS)
for i in range(START_INDEX, 0, -1):
    expanded_snippets = [snippet.expand(expand * 2) if snippet.type_name == "source" else snippet for snippet in snippets[:i]]
    proposed_snippets = organize_snippets(expanded_snippets[:i])
    cost = sum([len(snippet.get_snippet(False, False)) for snippet in proposed_snippets])
    if cost <= budget:                                   # SNIPPET_TOKEN_BUDGET = int(150_000 * 3.5)
        return proposed_snippets
raise Exception("Budget number of chars too low!")

# the assembled messages list is DISCARDED except as a join source; the pinned model never runs
joint_message = "\n\n".join(message.content for message in messages[1:])   # messages[0] (system) dropped
chat_gpt = ChatGPT(messages=[Message(role="system", content=context_files_to_change_system_prompt)])
MODEL = "claude-3-opus-20240229"
open("msg.txt", "w").write(joint_message + "\n\n" + context_files_to_change_prompt)
files_to_change_response = chat_gpt.chat_anthropic(
    content=joint_message + "\n\n" + context_files_to_change_prompt,
    model=MODEL, temperature=0.1, images=images, use_openai=use_openai,   # use_openai=True
)
# chat.py:371-375 — use_openai=True overrides the pinned model:
if use_openai:
    ...
    self.model = 'gpt-4o'

# parse_filenames — line-based strict filename-shape regex
pattern = r'^[^\/\.]+(\/[^\/\.]+)*\.[^\/\.]+$'
for possible_file in text.split("\n"):
    file_name = possible_file.strip()
    if re.match(pattern, file_name):
        file_names.append(file_name)
```

**Flow:** ticket_utils.get_relevant_context (the LIVE twin — see context-pruning-selection-plane) → context_get_files_to_change: interleave relevant[i]/read_only[i] alternately → `partition_snippets_if_test(include_tests=False)` drops every snippet whose path contains the substring "test" → `get_max_snippets`: walk i down from min(len, 15), expand source snippets ±600 lines (expand*2) for cost measurement, organize (fuse_distance=600), sum rendered-char cost, return the first prefix ≤ 525,000 chars, else raise → unconditional `[::-1]` reversal under a dead `if True:` flag → re-split by file_path membership against the ORIGINAL relevant list (a file present in both lists lands entirely in relevant) → render `<relevant_file index>` / `<read_only_snippet>` XML blocks (relevant source snippets expanded AGAIN ±300 lines at :1060) + reverse-import-graph section ("The file 'X' is imported by the following files", .venv/build paths skipped) + `<issue>` block + optional pr_diffs → ONE LLM call (gpt-4o via the use_openai override, temperature 0.1, NUM_ANTHROPIC_RETRIES=6, redis file_cache on call_anthropic) → parse `<relevant_files>` / `<read_only_files>` DOTALL blocks line-by-line through the strict filename regex → dict.fromkeys dedup → return two path lists. Caller rebuilds whole-file snippets with FileNotFoundError-skip and restores the pre-call deepcopy if BOTH lists are empty.
**Invariant:** The budget walk returns the LARGEST prefix that fits (walk-down, first-fit) — a port that walks up returns the smallest useful set instead. Raising when even one snippet exceeds budget means an oversized single file crashes the ticket rather than silently running with zero context; the PARSE side is the opposite posture — it tolerates empty output, and the caller's both-empty restore turns a garbage LLM answer into "use the pre-LLM context". The double expansion is real: the budget measures the organized ±600-line form, but the prompt renders relevant source at ±900 lines total (±600 from get_max_snippets + ±300 at :1060), so the shipped prompt can exceed the measured budget — a port that wants a true cap must measure the rendered string. The pinned `claude-3-opus-20240229` NEVER runs: `chat_anthropic(use_openai=True)` overwrites `self.model = 'gpt-4o'` (chat.py:375), so model pins passed through this path are advisory only while use_openai is set. The filename-shape regex rejects absolute paths, dotfiles, and extensionless names by construction — prose or absolute-path answers yield empty lists by design, not by accident. There is NO retry/repair loop at this step (contrast the FCR repair ladder in llm-plan-continuation-and-repair). The `open("msg.txt","w")` CWD write is a debug artifact repeated at three plan sites (:581/:896/:1132) — omit it.
**Probe:** No offline-runnable test exists for sweep_bot at pin (pass-2 finding stands: no direct unit tests for the planning plane; import chain needs openai/anthropic/redis). Deterministic probes executed at pin: `grep -n 'def context_get_files_to_change' sweepai/core/sweep_bot.py` → :1021 only; `grep -rn 'context_get_files_to_change' --include='*.py' sweepai/` → exactly 3 rows (def :1021, import ticket_utils.py:25, call ticket_utils.py:460 — single production caller); `grep -n 'msg.txt' sweepai/core/sweep_bot.py` → :581,:896,:1132; `grep -n 'max_snippets[::-1]' sweepai/core/sweep_bot.py` → :1049,:1204 (live + test-variant twin); `grep -n 'SNIPPET_TOKEN_BUDGET = ' sweepai/core/sweep_bot.py` → :62 only; `grep -n 'MAX_SNIPPETS = ' sweepai/core/sweep_bot.py` → :63 only (=15); `grep -n "self.model = 'gpt-4o'" sweepai/core/chat.py` → :375 only; `grep -n 'expand(300)' sweepai/core/sweep_bot.py` → :1060,:1250,:1418; `grep -n 'if True:' sweepai/core/sweep_bot.py` → :1048,:1227; `grep -n 'def get_max_snippets' sweepai/core/sweep_bot.py` → :346 with callers at :442/:750/:1047/:1203/:1392 (five plan variants share the same budget kernel); `grep -n 'parse_filenames' sweepai/core/sweep_bot.py` → def :181 + calls :1147,:1153 only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "context_get_files_to_change get_max_snippets parse_filenames relevant_files read_only_files", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// sweep_bot.py:181-200/:346-380/:1021-1156, entities.py:396-403, ticket_utils.py:443-502,
// chat.py:354-379 at pin substituted — see verification.md pass 4.
```

## Verdict
Adopt the interleave→test-partition→budget-walk→reverse pipeline as one named stage, the walk-down first-fit budget semantics (largest prefix that fits, raise on zero-fit), the strict filename-shape parser whose empty result is a SAFE default (caller restores pre-LLM context), and the single-caller contract that keeps the restore logic in one place. Adapt: measure the RENDERED prompt string for real token caps (not the pre-expansion form), make the reversal an explicit named decision, pass the model pin through only when the provider flag allows it, and replace the bare `Exception("Budget number of chars too low!")` with a typed error. Omit the msg.txt CWD writes, the dead model pin, the double expansion, and the substring-"test" partition (it drops non-test files like `latest.py`; match on path segments or a tests/ prefix instead). Coverage caveat: no live direct test at pin; the five shared get_max_snippets call sites mean a change to the budget kernel affects all plan variants.
