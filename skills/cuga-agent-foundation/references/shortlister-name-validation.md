<!-- capsule-v2 -->
# Shortlister name validation — how do you stop an LLM tool-ranker's hallucinated tool names from becoming runtime discoveries without burning 3× cost?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When the shortlister invents tool names (#546), when do you retry, when do you keep partial results, and what does the caller see?

## Bounded retry ladder in PromptUtils
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/prompt_utils.py:279` (`_SHORTLIST_NAME_MAX_RETRIES = 2`), `:286-316` (`_partition_shortlist_details`, `_shortlist_retry_instructions`), `:320-330` (`_format_filtered_tool_names_note`), `:332-360+` (`_ainvoke_shortlister_with_name_validation`). Pass-18 refresh (#624): the helpers STAY in PromptUtils but their only remaining caller is the `llm` strategy (`shortlister/llm.py:88-96`) — an embedding ranker draws names from the candidate list and cannot invent one, so it neither needs nor pays for retries; `find_tools`/`shortlist_tool_names` now consume strategy output and re-apply the historical filter only as defense-in-depth.
**Signature:** `async _ainvoke_shortlister_with_name_validation(*, chain, query, apps_as_dict, tools_as_dict, base_instructions, valid_names: set, run_config=None, max_retries=2) -> tuple[List[Any], List[str]]`.
**Data Shape:** returns `(valid_details, filtered_invalid_names)`; valid details accumulate across attempts keyed by name (first occurrence wins); invalid names accumulate uniquely in first-seen order.

### Decisive source
```python
if not invalid:
    return list(accumulated.values()), []
...
# Retry only when the shortlist is unusable — avoid 3x cost when
# mostly-valid results already have names we can keep.
if accumulated or attempt >= max_retries:
    break
instructions = PromptUtils._shortlist_retry_instructions(base_instructions or "", seen_invalid)
```

**Flow:** invoke chain → partition details into known vs unknown names (dedup by name) → clean result ⇒ return immediately → invalid names exist BUT some names were valid ⇒ KEEP the valid ones and STOP (no retry — retrying risks losing good results and costs a round-trip) → completely unusable AND attempts remain ⇒ re-invoke with feedback appended ("Your previous response included tool names that are not in the available tools list: … Reply again using ONLY exact names") → retries exhausted ⇒ drop unknowns forever (never forwarded as discoveries). Callers surface the dropped set as a markdown "Filtered out N unrecognized tool name(s): `x`, `y`" note.
**Invariant:** hallucinated names must NEVER reach the registry/executor as discoveries; retries fire only on total failure (empty `accumulated`), bounding cost at max 2 extra LLM calls; dedup is order-preserving for deterministic notes. The twin consumer `shortlist_tool_names` (:581-663) adds its own guards: whitespace-only query ⇒ `[]` WITHOUT invoking the LLM ("A whitespace-only query would otherwise invoke the LLM and produce arbitrary rankings"), top_k ≤ 0 ⇒ `[]`.
**Probe:** no direct unit test for this ladder (coverage caveat — deterministic check: response with 2 valid + 1 invented name returns the 2 valid immediately, one attempt only). The bind-tools cap module (bind-tools-cap capsule) raises loudly when ALL names are hallucinated — complementary contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_ainvoke_shortlister_with_name_validation _partition_shortlist_details", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the keep-partial-stop-early retry policy (retry ONLY when nothing usable came back) and never-forward-invalid-names guarantee for any LLM-as-selector component; adapt retry count, feedback wording, and the filtered-note format; omit the whitespace-query guard only if your callers pre-validate queries. Coverage caveat: source-read verified; the loud-failure sibling path is pinned by cap.py's error strings.
