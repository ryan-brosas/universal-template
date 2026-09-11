<!-- capsule-v2 -->
# autocommit diff commit message — how does the library write commit messages for prompt changes using itself?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I auto-generate human-meaningful version messages for prompt diffs without a human in the loop — and without recursing into tracking?

## dogfooded LMP over unified diff
**Path/Symbol:** `src/ell/util/differ.py:write_commit_message_for_diff` (:7-51); call site `src/ell/lmp/_track.py:serialize_lmp` (:228-238); model knob `config.autocommit_model` (default `"gpt-4o-mini"`, `src/ell/configurator.py` :79-82, :200).
**Signature:** `write_commit_message_for_diff(old: str, new: str) -> str` — decorated with `@simple(config.autocommit_model, temperature=0.2, exempt_from_tracking=True, max_tokens=500)`.
**Data Shape:** inputs are the joined `(dependencies + "\n\n" + source)` of old and new closure halves; BV/BmV tags stripped before diffing.

### Decisive source
```python
# _track.py:228-238
if config.autocommit:
    if not _autocommit_warning():
        from ell.util.differ import write_commit_message_for_diff

        commit = str(
            write_commit_message_for_diff(
                f"{latest_lmp.dependencies}\n\n{latest_lmp.source}",
                f"{fn_closure[1]}\n\n{fn_closure[0]}",
            )[0]
        )
```

```python
# differ.py:37-39 — placeholder markers must not pollute the diff
clean_program_of_all_bv_tags = lambda program : program.replace("# <BV>", "").replace("# </BV>", "").replace("# <BmV>", "").replace("# </BmV>", "")
```

**Flow:** on storing a NEW version when autocommit is on (and the user accepted the cost warning), the previous stored version's closure text vs the new one are cleaned of mutability-marker tags, unified-diffed inside the LLM's user prompt, and the system prompt (docstring) enforces ≤10 words, specificity ("what changed, not why"), and bulleted specifics. The decorator itself is `exempt_from_tracking=True` so generating a commit message never writes another invocation or triggers recursive versioning.
**Invariant:** the meta-call must be exempt from tracking AND from autocommit recursion; and tag-stripping must happen before diffing or every mutable-placeholder line reads as a change.
**Probe:** deterministic anchors from repo root: `grep -n 'exempt_from_tracking=True' src/ell/util/differ.py` → line 7 (the recursion-breaker); `grep -c 'BmV' src/ell/util/differ.py` == 2 (strip lambda mentions both open+close tags). No direct unit test at pin (needs an LLM key — coverage caveat recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "unified diff commit message", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.util.differ.write_commit_message_for_diff @ src/ell/util/differ.py:7-51
```

## Verdict
Adopt self-hosted commit messaging with tracking exemption. Adapt the prompt contract to your house style. Omit `_autocommit_warning` only if your product has no surprise-cost concern — but keep the exemption, it is what prevents infinite regress.
