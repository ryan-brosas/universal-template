<!-- capsule-v2 -->
# Provider alias classes — how are 10+ vendors onboarded without touching the core loop?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** What is the minimal extension surface for adding an LLM vendor, and where do model aliases resolve?

## Three-line subclass + class-attribute config; alias resolution at __init__
**Path/Symbol:** `os_computer_use/providers.py` (whole file, 9 concrete classes); `os_computer_use/llm_provider.py:40-43` (`LLMProvider.__init__`), `:103-106` (`OpenAIBaseProvider.create_client`).
**Signature:** subclass declares `base_url`, `api_key`, `aliases` as CLASS attributes; `__init__(self, model)` resolves via `self.aliases.get(model, model)` then builds client.
**Data Shape:** `aliases: {friendly_name: vendor_full_model_id}`; api_key pulled from env AT CLASS-BODY TIME (import-time snapshot — changing `os.environ` later has no effect).

### Decisive source
```python
class GroqProvider(OpenAIBaseProvider):
    base_url = "https://api.groq.com/openai/v1"
    api_key = os.getenv("GROQ_API_KEY")
    aliases = {"llama-3.2": "llama-3.2-90b-vision-preview",
               "llama-3.3": "llama-3.3-70b-versatile"}
```
```python
def __init__(self, model):
    self.model = self.aliases.get(model, model)
    print(f"Using {self.__class__.__name__} with {self.model}")
    self.client = self.create_client()
```

**Flow:** config.py instantiates three singletons (`grounding_model`, `vision_model`, `action_model`) with friendly names → constructor maps friendly→vendor id → all calls flow through the shared `completion()` of the chosen base family.
**Invariant:** Any OpenAI-compatible vendor needs ONLY base_url + api_key + aliases — no method overrides (Gemini rides the OpenAI spec via its `/v1beta/openai` endpoint). Alias miss falls back to the raw name, so new models work before aliases exist. Import-time env capture means dotenv must load BEFORE importing providers (both files call `load_dotenv()` defensively).
**Probe:** `cd /mnt/hdd/utopia/inspo/external/open-computer-use && grep -c '^class .*Provider(' os_computer_use/providers.py` → expect 10 (Llama/OpenRouter/Fireworks/DeepSeek/OpenAI/Gemini ride OpenAI-compatible; Anthropic; Groq; Mistral; Moonshot); `sed -n '17,29p' os_computer_use/providers.py` (Llama/OpenRouter alias tables verbatim).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "provider base_url aliases api_key getenv", limit: 10, fields: ["signature", "name", "file"] });
// expect the nine providers.py subclasses + LLMProvider.__init__ resolution
```

## Verdict
Adopt subclass-as-config onboarding for OpenAI-compatible vendor sprawl; adapt import-time env capture to lazy lookup if you rotate keys at runtime; omit per-vendor retry/timeout logic (deliberately absent — one concern per layer).
