<!-- capsule-v2 -->
# py-ollama-chunk-size-override — why do user chunk params silently change for Ollama, and when?

**Source:** meetily (MIT) `main@0281737d87d26352fb0adc78c8c0975f691b23d1`; Codebase Memory `ext-meetily`. **Question:** A porter copying the chunked-summary API must know when the caller's `chunk_size`/`overlap` are honored and when they are overwritten per provider.

## Provider-conditional parameter override
**Path/Symbol:** `backend/app/transcript_processor.py:TranscriptProcessor.process_transcript` (:87-166).
**Signature:** `async def process_transcript(self, text: str, model: str, model_name: str, chunk_size: int = 5000, overlap: int = 1000, custom_prompt: str = "") -> Tuple[int, List[str]]`.
**Data Shape:** Returns `(num_chunks, list[json_str])`. For `model == "ollama"` the function REWRITES its own locals after model selection: small local models (`phi4*`, `llama*`, case-insensitive prefix) get `(10000, 1000)`; any other Ollama model gets `(30000, 1000)`. Cloud providers (`claude|groq|openai`) keep caller values.

### Decisive source
```python
if model_name.lower().startswith("phi4") or model_name.lower().startswith("llama"):
    chunk_size = 10000
    overlap = 1000
else:
    chunk_size = 30000
    overlap = 1000
```

**Flow:** provider select → (ollama only) override sizes → guard degenerate overlap → split → per-chunk summarize.
**Invariant:** The Ollama branch bypasses pydantic_ai entirely (`chat_ollama_model` :235 talks raw `AsyncClient.chat(stream=True, format=SummaryResponse.model_json_schema())`), so the JSON-schema-forced path and the agent path see DIFFERENT chunk sizes by design; a porter who "fixes" the override breaks context-window fit for local models. Degenerate-input guard at :158-162: if `overlap >= chunk_size`, overlap is clamped to `chunk_size - 100` so `step` stays positive.
**Probe:** `grep -cF 'chunk_size = 30000' backend/app/transcript_processor.py` → `1` (battery P1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "process_transcript chunk_size ollama override", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the provider-conditional size table + step guard as behavior; adapt thresholds to your models' context windows; omit the hardcoded prompt text inside the f-string (product copy). Direct tests absent for this module — coverage caveat recorded in work record (backend has no test suite).
