<!-- capsule-v2 -->
# Capability settings merge + Thinking capability — per-capability ModelSettings fold

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/thinking.py` (whole, 30L) + `capabilities/abstract.py` `get_model_settings` contract + `settings.py` ThinkingLevel (:9–22) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Multiple composable capabilities each want a say in model settings (thinking level, max tokens, temperature) — how do you let them contribute WITHOUT one clobbering another, and keep the whole thing spec-serializable so users can declare capabilities as data? A porter will give each capability its own settings field and let the last writer win.

## Path / Symbol
`thinking.py` — `Thinking(effort: ThinkingLevel = True)` dataclass with `get_model_settings()`; `test_capabilities.py::test_combined_capability_get_model_settings_merge` (:2812) documents the CombinedCapability fold: sub-capability dicts MERGE key-wise (`max_tokens=100` + `temperature=0.5` coexist), None from every contributor → overall None (:2838–2846); deferred capabilities contribute only once loaded (:2849+).

## Signature
```python
@dataclass
class Thinking(AbstractCapability[Any]):
    effort: ThinkingLevel = True   # True | False | 'minimal'|'low'|'medium'|'high'|'xhigh'
    def get_model_settings(self) -> ModelSettings | None:
        return ModelSettings(thinking=self.effort)
```

## Data Shape
`ThinkingLevel = bool | Literal['minimal','low','medium','high','xhigh']`. The unified `ModelSettings.thinking` key is provider-portable: providers without native support map to the closest level ('xhigh'→'high', 'minimal'→'low'); provider-specific keys (`anthropic_thinking`, `openai_reasoning_effort`) take precedence when BOTH are set. `get_model_settings` may also return a CALLABLE for step-aware values — which is exactly what the static tool_choice gate trusts.

### Decisive source — the merge probe's assertions (:2831–2835)
```python
merged = caps.get_model_settings()
assert merged is not None
assert not callable(merged)          # static contributors fold to a plain dict...
assert merged.get('max_tokens') == 100
assert merged.get('temperature') == 0.5   # ...with sibling keys preserved, not replaced
```
Spec-serialization interplay: `Thinking` HAS a serialization name (data of scalars); callable-taking capabilities like PrepareTools return `get_serialization_name() → None` ("Not spec-serializable") — the same test file pins both classes in generated specs (:1746–1749 `'spec_Thinking'`).

**Flow:** agent run → collect get_model_settings from active capabilities → dict-merge contributions (later same-key wins by fold order) → merged dict (or callable) feeds the request-settings path → provider maps unified keys to wire fields with closest-level fallbacks.

**Invariant:** Capability-contributed settings compose by KEY MERGE over an open TypedDict, never by field assignment; None means "no opinion" and must vanish from the fold; serializability is opt-in per capability class and enforced in generated-spec tests.

**Probe:** `tests/test_capabilities.py::test_abstract_capability_get_model_settings_default` (:2634), `test_combined_capability_get_model_settings_merge` (:2812), `test_combined_capability_get_model_settings_none` (:2838), `test_combined_capability_get_model_settings_deferred` (:2849); unified-key merge semantics pinned by `tests/test_settings.py::TestMergeModelSettingsThinking` (:86+ — bool/effort override, sibling keys preserved).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'Thinking get_model_settings CombinedCapability merge'
```

## Verdict
**Adopt** the open-dict key-merge fold and the scalar-only ⇒ serializable rule. **Adapt** level vocabularies. **Omit** vendor-specific setting names.
