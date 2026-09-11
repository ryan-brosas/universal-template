<!-- capsule-v2 -->
# Nested-history ownership rebase — how does forwarded-item ownership survive input mutation without claiming the wrong slot?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** After a handoff forwards items into nested history (each recorded as an owned ref with index + digest + occurrence key), how do you keep those ownership refs valid when the input list is copied, reordered, rewritten, or resumed — and how do you refuse to claim ownership when an equal-but-unidentifiable occurrence makes the match ambiguous?

## Digest-first, identity-second rebase protocol with ambiguity rejection
**Path/Symbol:** `src/agents/run_internal/items.py:` `nested_history_run_item_occurrence_key` (:114–119), `ensure_nested_history_run_item_occurrence_key` (:122–128), `digest_input_item` (:393–412), `filter_nested_history_owned_item_refs_for_input` (:415–462), `reconcile_nested_history_owned_input_after_rewrite` (:465–563), `resolve_nested_history_owned_item_indexes` (:570–629), `rebase_nested_history_owned_item_refs` (:633–678); consumer `src/agents/result.py:` `_populate_state_from_result` (:129–131); resume call site `src/agents/run_internal/run_loop.py` (:1068–1073).
**Signature:** `rebase_nested_history_owned_item_refs(input, run_items, owned_item_refs) -> list[NestedHistoryOwnedItemRef]`; `reconcile_nested_history_owned_input_after_rewrite(previous_input, rewritten_input, owned_item_refs) -> tuple[str | list[TResponseInputItem], list[NestedHistoryOwnedItemRef]]`.
**Data Shape:** a `NestedHistoryOwnedItemRef` carries `input_index`, `input_item`, `session_index`, `run_item`, and a content `digest`; matching keys are `(id(object), digest)` identity pairs and `(occurrence_key, digest)` copy-lineage pairs, each mapped to a `deque` of candidate indexes.

### Decisive source
```python
# digest_input_item: normalize BEFORE hashing so cosmetic differences don't break matches
if coerced.get("role") == "assistant":
    if isinstance(content, str):
        coerced["content"] = [{"type": "output_text", "text": content}]
    if coerced.get("status") in {None, "completed"}:
        coerced.pop("status", None)
return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

# reconcile: digest-only fallback ONLY when the rewrite is unambiguous
all_equal_occurrences_owned = (
    previous_count == rewritten_count == recoverable_ref_counts.get(item_ref.digest, 0)
)
if (not previous_match
    or rewritten_count <= used_digest_counts.get(item_ref.digest, 0)
    or not ((previous_count == 1 and rewritten_count == 1) or all_equal_occurrences_owned)):
    continue                                  # ambiguous → drop ownership, never guess

# rebase: stored index validated first, then candidate deques, min wins, no double claims
if (0 <= stored_index < len(run_items) and stored_index not in resolved
    and run_item_digests[stored_index] == item_ref.digest
    and (run_items[stored_index] is item_ref.run_item
         or occurrence_keys_match)):
    resolved.add(stored_index); continue
candidates = [i for i in (identity_index, occurrence_index) if i is not None]
if candidates:
    resolved.add(min(candidates))
```

**Flow:** ownership is rebased at three points, each stricter than the last. (1) `filter_nested_history_owned_item_refs_for_input` runs against the live input: a ref survives only if its exact clean occurrence is still present — an identity deque walk `(id(input_item), digest)` first, with a digest-only fallback permitted ONLY for refs whose `input_item` object was lost (None). (2) `reconcile_nested_history_owned_input_after_rewrite` handles resume input rewrites: identity matches always win; a digest-only match is allowed only when the rewrite is provably unambiguous — either exactly one occurrence before AND after, or every equal occurrence on both sides is itself owned (`previous_count == rewritten_count == recoverable_ref_counts[digest]`); any other shape drops the ref. (3) `rebase_nested_history_owned_item_refs` (called from `_populate_state_from_result` when populating state) validates the stored session index first (digest + identity-or-occurrence-key), then falls back to identity/occurrence candidate deques, takes `min(candidates)`, and a shared `used_indexes` set prevents two refs from claiming one slot. Repeated occurrences of the SAME RunItem object stay distinguishable via a private copy-lineage occurrence key (a uuid bound to the object that survives copies but never enters model payloads).
**Invariant:** rebasing fails closed on ambiguity — copied payloads never claim ownership of an equal-but-unidentifiable occurrence (dropped refs simply lose their provenance protection rather than mis-protect a different item), digests are computed over normalized items so cosmetic differences don't break matches, and one live slot can satisfy at most one ref.
**Probe:** `tests/test_handoff_history_duplication.py::test_nested_history_input_rebase_rejects_ambiguous_equal_occurrences` (:1001 — deep-copied equal forwarded item appended → `_get_nested_history_owned_items(rebuilt) == ()`), `::test_nested_history_preserves_repeated_run_item_reference_occurrences` (:1029 — repeating one RunItem keeps both logical occurrences in replay input), `::test_nested_history_ownership_remaps_after_new_items_insertion` (:1159), `::test_nested_history_input_removal_does_not_claim_an_unmarked_equal_occurrence` (:1181), `::test_nested_history_input_copy_does_not_infer_occurrence_ownership` (:1262), `::test_nested_history_input_copy_and_reorder_does_not_infer_ownership` (:1302).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "items.py", query: "rebase nested history owned item refs ambiguous", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.items.rebase_nested_history_owned_item_refs" });
```

## Verdict
Adopt the three-point rebase protocol (filter → reconcile → rebase) with normalized-content digests, identity-first/occurrence-second candidate deques, min-wins slot selection with a used-set, and fail-closed ambiguity rejection for any system that tracks per-occurrence ownership of items across copies, rewrites, and resume. Adapt the ref fields and the unambiguity predicate. Omit the copy-lineage occurrence key if you never forward the same object twice. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); decisive ranges read from checkout at fe45b415.
