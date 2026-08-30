<!-- capsule-v2 -->
# Standalone knowledge-package host bridge — how do you keep a RAG package dependency-free while still using the host app's LLM?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your retrieval engine lives in a standalone package but needs LLM calls (query rewriting) — how do you wire the host's model in without the package importing host code?

## Dependency INVERSION at one Protocol seam: package defines `generate(prompt)->str`, host adapts and injects; lazy model build
**Path/Symbol:** `src/cuga/backend/knowledge_llm_bridge.py` — whole file 32L (`CugaChatGenerator`); Protocol side: `knowledge/query_transform.py:37-40` (`class ChatGenerator(Protocol): async def generate(self, prompt) -> str`).
**Signature:** `CugaChatGenerator().async generate(prompt: str) -> str`; model resolved on FIRST call via `LLMManager().get_model(settings.agent.code.model)` then cached on the instance.
**Data Shape:** response normalized to plain string: `content = getattr(resp, "content", resp); return content if isinstance(content, str) else str(content)`.

### Decisive source
```python
# :24-32 — the entire bridge: lazy + duck-typed, zero knowledge/ imports here
async def generate(self, prompt: str) -> str:
    if self._model is None:
        from cuga.backend.llm.models import LLMManager
        from cuga.config import settings
        self._model = LLMManager().get_model(settings.agent.code.model)
    resp = await self._model.ainvoke(prompt)
    content = getattr(resp, "content", resp)
    return content if isinstance(content, str) else str(content)
```
**Flow:** KnowledgeEngine constructs fine before cuga's LLM is ready (no model built at init) → first query-transform call triggers lazy model resolution → prompt in, completion text out → knowledge package's fail-open wrapper (see query-transform capsule) handles any error.
**Invariant:** (1) The bridge lives OUTSIDE `knowledge/` precisely so the package never imports cuga internals — moving it inside reintroduces the coupling the Protocol exists to break. (2) Non-string contents (blocks/lists) are str()'d rather than raised — the consumer's fail-open contract prefers degraded input over exceptions. (3) Uses the CODE agent's model, not the planner's — query rewriting is a cheap task that should ride the strongest configured default.

**Probe:** No direct unit suite for the bridge itself at HEAD (coverage caveat — 32L composition class; its consumer behavior is pinned by `tests/unit/test_knowledge_query_transform.py` end-to-end HyDE test which injects a fake generator through this exact Protocol).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CugaChatGenerator ChatGenerator protocol generate bridge", limit: 8 });
```
## Verdict
Adopt whenever extracting a subsystem into a reusable package that still wants the host's models: define the narrowest Protocol INSIDE the package, adapt lazily OUTSIDE it.
