<!-- capsule-v2 -->
# Bedrock multi-provider dispatch — how does one SDK class serve a dozen Bedrock model families with per-provider message shapes and inference-config exclusions?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how is the provider derived from a model ID (and overridden), which providers take which message format and Converse-vs-invoke_model path, and where do capability tables (tools/vision/streaming) plus temp+topP mutual-exclusion live?

## Connected graph-selected seam
**Path/Symbol:** `mem0/llms/aws_bedrock.py`: `PROVIDERS` roster (:19-23), `extract_provider` (:26-37), `_initialize_provider_settings` (:126-149, MiniMax tools-exclusion comment :130-133), five `_format_messages_*` variants (:151-240), `_prepare_input` provider param-mapping table (:248-324), response-field ladder `_parse_response` (:363-433), `_build_inference_config` (:500-522), `_generate_with_tools` (:524-560) vs `_generate_standard` routing (:562-652), Nova reasoningContent scan (:618-621). Direct tests `tests/llms/test_aws_bedrock.py` (`test_standard_anthropic_model`…`test_unknown_model_raises`, `test_application_inference_profile_arn_without_override_raises`, `test_explicit_provider_takes_precedence_over_regex`, top_p default/set/getModelConfig matrix :95-123).
**Signature:** `extract_provider(model: str, explicit_provider: Optional[str] = None) -> str`; `_format_messages_anthropic(messages) -> tuple[list, Optional[str]]` vs Cohere/Meta `-> str` vs Amazon/Mistral `-> list`; `_prepare_input(prompt: str) -> Dict`.
**Data Shape:** model IDs are Bedrock strings `provider.model-name[:region-suffix]` or application-inference-profile ARNs; capabilities are three frozen membership tables — supports_tools {anthropic,cohere,amazon} (MiniMax deliberately EXCLUDED: tool use only via bedrock-mantle endpoint, not Converse), supports_vision {anthropic,amazon,meta,mistral}, supports_streaming {anthropic,cohere,mistral,amazon,meta}.

### Decisive source
```python
def extract_provider(model, explicit_provider=None):
    if explicit_provider:
        if explicit_provider not in PROVIDERS:
            raise ValueError(f"Unknown provider_override ...")     # typo LOUD, never silent guess
        return explicit_provider                                   # override beats regex
    for provider in PROVIDERS:
        if re.search(rf"\b{re.escape(provider)}\b", model):        # word-boundary match
            return provider
    raise ValueError(f"Unknown provider in model: {model}")

def _build_inference_config(self):
    inference_config = {"maxTokens": ..., "temperature": ...}
    if top_p is not None:
        if self.provider in ("anthropic", "minimax"):
            pass  # BOTH raise ValidationException when temperature and topP coexist → omit topP
        else:
            inference_config["topP"] = top_p
```
```python
# per-provider request-body key mapping (invoke_model path)
provider_mappings = {
    "meta": {"max_tokens": "max_gen_len"},
    "ai21": {"max_tokens": "maxTokens", "top_p": "topP"},
    "cohere": {"max_tokens": "max_tokens", "top_p": "p"},   # Cohere calls it "p"
    "amazon": {"max_tokens": "maxTokenCount", "top_p": "topP"},
}
# response text extraction ladder by provider field name:
anthropic→content[0].text | nova→content[0].text|completion | legacy-amazon→completion
meta→generation | mistral→outputs[0].text | cohere→generations[0].text
ai21→completions[0].data.text | generic→first of content/text/completion/generation → str(json)
```

**Flow:** ctor normalizes config → boto3 client + `_test_connection` (list_foundation_models; failure only WARNS and leaves `available_models=[]`) → `extract_provider` pins self.provider → `_initialize_provider_settings` sets capability flags AND binds `self._format_messages` to the provider variant → `generate_response` routes: tools ∧ supports_tools ⇒ `_generate_with_tools` (Converse API; Anthropic system hoisted to top-level `system=[{"text":...}]`) else `_generate_standard`, itself split Anthropic-always-Converse / MiniMax-Converse-with-reasoningContent-scan / Nova-Converse / everyone-else invoke_model with JSON body from `_prepare_input`. Parse failures degrade to the string `"Error parsing response"` after a warning.
**Invariant:** (1) provider detection is loud at both ends — unknown model raises, misspelled override raises, but a valid override beats the regex (ARNs carry no provider token); (2) message-format RETURN TYPES differ per provider (tuple-with-system vs plain-string prompt vs list) — callers must not assume one shape; (3) temperature+topP mutual exclusion is enforced by OMitting topP for anthropic/minimax, mirroring the Anthropic direct-client rule; (4) Nova reasoning models interleave `reasoningContent` blocks before text — parse by scanning for the first block containing `"text"`, not index 0; (5) every invoke_model body key differs per provider (max_gen_len/maxTokens/p/maxTokenCount/max_tokens) — one shared body shape fails six ways.
**Probe:** `tests/llms/test_aws_bedrock.py::TestExtractProvider::test_unknown_model_raises` + `test_explicit_provider_typo_raises` + `test_arn_with_provider_override_resolves`; `::test_get_model_config_excludes_top_p_by_default` / `::test_get_model_config_includes_top_p_when_set`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "extract_provider _format_messages_anthropic _build_inference_config converse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the roster+override detection, the three capability tables, and the temp/topP omission rule verbatim; adapt provider mappings/response-field ladders to whichever Bedrock families you actually serve (keep the loud-unknown contract); omit the legacy invoke_model plane entirely if you only target Converse-API models.
