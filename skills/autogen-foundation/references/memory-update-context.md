<!-- capsule-v2 -->
# Memory update-context protocol — who fetches relevance and who mutates the prompt when memory enters an LLM context?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** How should pluggable memory stores inject content into a model context without the agent knowing their retrieval strategy?

## Mutate-and-report: the store updates the context AND returns what it added
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/memory/_base_memory.py` `Memory` ABC :60–131 (`update_context` :77–91); `python/packages/autogen-core/src/autogen_core/memory/_list_memory.py` `ListMemory.update_context` :104–129; vector variant `python/packages/autogen-ext/src/autogen_ext/memory/chromadb/_chromadb.py` `ChromaDBVectorMemory.update_context` :310–333; agent glue `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py` `_update_model_context_with_memory` :1028–1053.
**Signature:** `async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult` · `UpdateContextResult(memories: MemoryQueryResult(results: List[MemoryContent]))`.
**Data Shape:** `MemoryContent{content: str|bytes|dict|Image, mime_type, metadata}`; injection vehicle is ONE `SystemMessage`; retrieval query source differs per implementation.

### Decisive source
```python
# ListMemory — everything, chronologically, as ONE numbered SystemMessage
memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(self._contents, 1)]
memory_context = "\nRelevant memory content (in chronological order):\n" + "\n".join(memory_strings) + "\n"
await model_context.add_message(SystemMessage(content=memory_context))
return UpdateContextResult(memories=MemoryQueryResult(results=self._contents))
```
```python
# ChromaDBVectorMemory — relevance comes from the CURRENT conversation tail
messages = await model_context.get_messages()
last_message = messages[-1]
query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)
query_results = await self.query(query_text)
```
```python
# Agent-side glue stays strategy-free: iterate stores, convert non-empty results to events
for mem in memory:
    update_context_result = await mem.update_context(model_context)
    if update_context_result and len(update_context_result.memories.results) > 0:
        events.append(MemoryQueryEvent(content=update_context_result.memories.results, source=agent_name))
```

**Flow:** before the LLM call the agent iterates configured stores calling `update_context(model_context)` → the STORE decides retrieval (List: append-all chronological; vector: query built from the LAST message's text) → store appends its own `SystemMessage` → non-empty results become `MemoryQueryEvent`s for observability.
**Invariant:** `update_context` MUTATES the passed context and its return value MIRRORS exactly what it added — callers never re-read the context to learn what changed; an empty store is a no-op returning empty results (no placeholder message); the query-extraction contract ("last message, stringified") is the only thing a vector store needs from the conversation.
**Probe:** `python/packages/autogen-core/tests/test_memory.py::test_list_memory_update_context` (:134–147 — two added memories ⇒ ONE context SystemMessage containing both; `results.memories.results` length 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ qualified_name: "autogen.python.packages.autogen-ext.src.autogen_ext.memory.chromadb._chromadb.ChromaDBVectorMemory.update_context", project: "autogen" });
```

## Verdict
Adopt mutate-and-report memory injection for any host with swappable retrieval backends — it keeps the agent loop storage-agnostic. Adapt storage engines freely (list/vector/redis/mem0 all satisfy the same ABC). Omit the chromadb/Mem0 client configuration surfaces; they are stack-specific adaptation territory.
