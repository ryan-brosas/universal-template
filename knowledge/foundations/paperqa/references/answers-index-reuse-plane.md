<!-- capsule-v2 -->
# Answers-index reuse plane — where do finished Q&A runs go so later runs (and the CLI) can retrieve them?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** How is every completed `agent_query` recorded into a persistent searchable index, and how is that index read back without knowing the storage internals?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/main.py:agent_query` (:54-85), `index_search` (:408-437).
**Signature:** `async def agent_query(query, settings, docs=None, agent_type=DEFAULT_AGENT_TYPE, **runner_kwargs) -> AnswerResponse`; `async def index_search(query: str, index_name: str = "answers", **index_kwargs) -> list[tuple[AnswerResponse, str] | tuple[Any, str]]`.
**Data Shape:** answers index: fields `REQUIRED_FIELDS + ["question"]`, `storage=SearchDocumentStorage.JSON_MODEL_DUMP`, doc = `{file_location: str(session.id), body: answer, question}` with the full `AnswerResponse` stored as blob. Non-"answers" index names fall back to pickle-compressed Docs blobs and REQUIRED_FIELDS only.

### Decisive source
```python
answers_index = SearchIndex(fields=[*SearchIndex.REQUIRED_FIELDS, "question"],
                            index_name="answers",
                            index_directory=settings.agent.index.index_directory,
                            storage=SearchDocumentStorage.JSON_MODEL_DUMP)
response = await run_agent(docs, query, settings, agent_type, **runner_kwargs)
await answers_index.add_document({"file_location": str(response.session.id),
                                  "body": response.session.answer,
                                  "question": response.session.question},
                                 document=response)
await answers_index.save_index()
...
# index_search
results = [(AnswerResponse(**a[0]) if index_name == "answers" else a[0], a[1])
           for a in await index_to_query.query(query=query, keep_filenames=True)]
```

**Flow:** run the agent → unconditionally record the finished response into the shared "answers" tantivy index in the SAME index directory as paper indexes → save immediately → later, `index_search` rehydrates each hit as `AnswerResponse(**dict)` because JSON storage round-trips BaseModel fields by name, pairing each with its filename (= session id) via `keep_filenames=True`.
**Invariant:** Recording happens for EVERY completed run — including UNSURE/TRUNCATED failover answers — so the answers index is append-only ground truth of what was previously asked/answered; it shares `index_directory` but has a distinct index name, i.e. answer reuse rides exactly the same lock/save/hydration machinery as paper search (one implementation, two corpora). The `question` field exists ONLY on this index so question-text search works; the body searched is the ANSWER text.
**Probe:** `tests/test_cli.py::test_cli_ask` (:51-69) pins that a CLI ask returns an `AnswerResponse` equal to the original run's (`found_answer.model_dump() == response.model_dump()`), exercising the JSON round-trip; source :411-415 pins the conditional storage/field selection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "index_search answers AnswerResponse table_formatter", limit: 10 });
// trace_path --function-name agent_query --direction outbound → run_agent, add_document, save_index
```

## Verdict
Adopt "every completed run becomes a searchable row in a same-machinery side index" for agent products needing recall/dedup/analytics; adapt storage to your language boundary (JSON when non-Python readers exist); omit the Rich table rendering and the Docs-blob fallback branch if you only have one corpus kind. Coverage caveat: cited paths `no_recorded_issue` + `metadata_match`; the CLI ask path is pinned through test_cli.py although cli.py itself is graph-silent (see work record).
