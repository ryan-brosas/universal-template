<!-- capsule-v2 -->
# continuation merge primitives — how are suspended segments classified, folded, and bounded?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What is the provider-agnostic contract for classifying a continuation (replace vs accumulate), folding its parts/usage/metadata, and bounding runaway suspension chains — independent of any one provider adapter?

## merge_mode / merge_responses / ceilings (`models/_continuation.py`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/_continuation.py:merge_mode` (:149-163), `merge_responses` (:166-213), `MAX_GENERATION_CONTINUATIONS = 10` (:70), `MAX_BACKGROUND_POLLS = 1000` (:85), `MergeMode = Literal['replace-same-id','replace-new','accumulate']` (:99).
**Signature:** `merge_mode(existing: ModelResponse, new: ModelResponse) -> MergeMode`; `merge_responses(existing, new) -> ModelResponse`.
**Data Shape:** Classification inputs: `provider_response_id`, `model_name`, and a framework metadata marker `metadata['__pydantic_ai__']['replace_previous_response']`. Output fields folded: `parts`, `usage`, `provider_response_id`, `provider_details`, `metadata`.

### Decisive source
```python
# _continuation.py:149-163 — the single decision path shared by merging, BOTH ceilings,
# and the streamed composite's part-index reindexing
def merge_mode(existing, new):
    if _has_replace_marker(new):                       # FallbackModel directive wins first
        return 'replace-new'
    if existing.provider_response_id and existing.provider_response_id == new.provider_response_id:
        return 'replace-same-id'                       # passive re-poll of ONE background job
    if existing.model_name and new.model_name and existing.model_name != new.model_name:
        return 'replace-new'                           # accumulating parts across models is always wrong
    return 'accumulate'                                # Anthropic pause_turn

# :178-191 — replace keeps prior usage for fresh generation; same-job polling takes the
# new cumulative snapshot; accumulate concatenates parts and sums usage
if mode == 'replace-same-id':
    merged = new
elif mode == 'replace-new':
    merged = replace(new, usage=existing.usage + new.usage)
else:
    merged = replace(new,
        parts=[*existing.parts, *new.parts],
        usage=existing.usage + new.usage,
        provider_response_id=new.provider_response_id or existing.provider_response_id)
```

## Transient replace-marker protocol
`_has_replace_marker` (:120-126) / `_strip_replace_marker` (:129-146): the marker means "this response supersedes the suspended turn" even when id/model would classify as accumulate. It is honored once then **popped** (copy-on-write through the shared `__pydantic_ai__` namespace) so it cannot persist into history and wrongly force a later legitimate `pause_turn` to replace. Sibling namespace keys (e.g. the FallbackModel continuation pin) survive the strip.

**Flow:** every continuation fold: classify → merge by mode → merge turn-scoped `provider_details`/`metadata` latest-wins over existing (:201-204, so a mid-flight-cancel segment that never stamped the pin still inherits it) → strip the transient marker. Ceiling selection is keyed on the PREVIOUS merge's mode (`last_mode`): `'replace-same-id'` counts against 1000 polls (one long-running job; usage limits can't bound a tokenless pending poll), everything else counts against 10 fresh-generation continuations; exceeding either raises `UnexpectedModelBehavior`.

**Invariant:** One taxonomy drives three consumers (merge, ceiling count, stream reindexing) so they can never disagree. Fresh-generation replacements RETAIN prior billed usage (the old generation was really served); same-job replacement REPLACES usage wholesale (each poll returns the cumulative snapshot). The replace marker is single-shot.

**Probe:** `tests/models/test_continuation_stream.py::test_replace_previous_marker_forces_replace_and_is_stripped` (:966 — marker flips an accumulate to replace, sibling pin survives, follow-up merges accumulate); `::test_replace_poll_chain_runs_past_max_generation_continuations` (:864 — same-id chain sails past 10); `::test_model_change_replace_chain_counts_against_strict_ceiling` (:912).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "merge_mode merge_responses MAX_BACKGROUND_POLLS replace_previous_response", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way classification keyed on (marker, response-id equality, model change) with one shared decision function; adopt the dual-ceiling split (same-job poll vs fresh generation) and the transient-marker pop. Adapt the marker's metadata namespace to your host. Omit nothing — this module is deliberately dependency-free (only models/messages/usage/exceptions + stdlib) and ports as-is. Coverage clean at the pinned commit.
