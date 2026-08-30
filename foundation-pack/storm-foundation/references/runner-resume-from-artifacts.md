<!-- capsule-v2 -->
# Runner resume-from-artifacts — how does a four-stage pipeline let you stop and restart at any stage without recomputation?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What file contract makes each pipeline stage independently skippable, and where do stage outputs land?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/engine.py:STORMWikiRunner.run` (:341-442) + `_load_*_from_local_fs` helpers (:312-339).
**Signature:** `run(topic, ground_truth_url="", do_research=True, do_generate_outline=True, do_generate_article=True, do_polish_article=True, remove_duplicate=False, callback_handler=BaseCallbackHandler())`.
**Data Shape:** `output_dir/<topic_with_spaces_and_slashes_as_underscores>/` holding: `conversation_log.json` + `raw_search_results.json` (research), `storm_gen_outline.txt` + `direct_gen_outline.txt` (outline), `storm_gen_article.txt` + `url_to_info.json` (draft), `storm_gen_article_polished.txt` (polish), plus post-run `run_config.json` + `llm_call_history.jsonl`.

### Decisive source
```python
self.article_dir_name = truncate_filename(topic.replace(" ", "_").replace("/", "_"))
# per-stage guard: if the upstream object is None because its stage was skipped,
# reload from the artifact the skipped stage would have written:
if information_table is None:
    information_table = self._load_information_table_from_local_fs(
        os.path.join(self.article_output_dir, "conversation_log.json"))
if outline is None:
    outline = self._load_outline_from_local_fs(topic=topic, ...)
...
assert os.path.exists(draft_article_path), makeStringRed(
    f"... Please set --do-generate-article argument to prepare ...")   # loud, actionable
```

**Flow:** Each stage writes its artifacts IMMEDIATELY on completion → a later stage with `do_<prev>=False` loads from disk instead of memory → missing artifacts produce an assert whose message names the exact flag to run first. `post_run()` dumps LM kwargs config and drains call history (popping `kwargs` from each entry before JSONL write). The decorator machinery wraps every `run_*` so even a resumed stage's usage lands in the ledger.
**Invariant:** (1) Artifact filenames are part of the public contract — renaming breaks resume. (2) Topic string IS the directory key after `_`-substitution + 125-char truncation; two topics colliding after substitution share a directory. (3) `information_table`/`outline`/`draft_article` flow forward in-memory when earlier stages ran — loading happens ONLY on None. (4) At least one `do_*` must be true or run asserts immediately.
**Probe:** deterministic pins GREEN — engine.py:206-210 (`init_check` + `apply_decorators` wiring) and interface.py `run_` prefix byte-verified this pass; loader assert messages read at :312-339.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "STORMWikiRunner run module resume", limit: 10 });
```

## Verdict
Adopt the artifact-per-stage + load-on-None pattern for any long multi-stage LLM pipeline; adapt filenames/flags; omit the print-red assert style in favor of typed errors. Note the five-slot LM config (`conv_simulator_lm`, `question_asker_lm`, `outline_gen_lm`, `article_gen_lm`, `article_polish_lm`) is what makes per-stage cost/quality tuning possible. Caveat: no upstream tests; source-pinned.
