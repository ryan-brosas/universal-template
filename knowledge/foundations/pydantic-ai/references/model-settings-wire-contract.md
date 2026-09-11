<!-- capsule-v2 -->
# ModelSettings doc-tested wire contract — "Supported by" lists are parsed and CI-enforced

## Source / Question
`pydantic_ai_slim/pydantic_ai/settings.py` (:82–106 docstring contract, :108+ field entries, :240–278 tool_choice entry) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A cross-provider settings TypedDict drifts constantly — a field documented as supported gets dropped on one interface, or a doc bullet rots after a provider changes behavior. How do you keep the settings documentation TRUTHFUL at machine level? A porter will write prose docs and accept silent rot.

## Path / Symbol
`settings.py` — `ModelSettings(TypedDict, total=False)`; `ThinkingEffort`/`ThinkingLevel` aliases (:9–22); `ServiceTier` unified value set with per-provider mapping table + precedence rule (:45–79); `ToolOrOutput` dataclass (:27–40); `ToolChoice` alias + static-use constraint (:42–43, :240+).

## Signature
```python
class ModelSettings(TypedDict, total=False):
    """...
    Each field's `Supported by:` list names the model classes that put the setting on the wire. A bare
    name covers every interface that model serves ... a name qualified with an interface, like
    `OpenAI Chat Completions`, covers only that one ...
    These lists are parsed and checked against the wire by
    `tests/models/test_model_settings_support.py`, so keep the `* Name` bullet shape and put any nuance in
    parentheses after the name.
    ...
    Being listed means Pydantic AI sends the setting, not that the service honors it.
    """
    max_tokens: int
    """... Supported by: * OpenAI * Anthropic * Google * Groq ..."""
```

## Data Shape
The docstring is a PARSED ARTIFACT: `* Name` bullets under `Supported by:` are machine-checked against what each model class actually serializes (test file named IN the docstring). Nuance goes in parentheses AFTER the name; the honest boundary sentence — "listed means sent, not honored" — is part of the contract.

### Decisive source — scope-precision rules (:88–97)
```python
# A bare name covers every interface that model serves, so `OpenAI` means both
# [OpenAIChatModel] and [OpenAIResponsesModel]; a name qualified with an interface, like
# `OpenAI Chat Completions`, covers only that one, because the Responses API does not
# accept the setting at all.
```
`service_tier` shows the second pattern: a UNIFIED value set ('auto'/'default'/'flex'/'priority') with an explicit per-provider mapping table (omitted vs mapped vs header-based), plus the precedence rule that provider-specific fields always win when set — and values outside the unified set reachable ONLY through per-provider fields.

**Flow:** author adds a settings field → writes `Supported by:` bullets in exact shape → CI test parses the docstring, asserts each listed model actually puts the field on the wire (and vice versa for qualified names) → docs can never silently lie.

**Invariant:** Documentation that makes claims about behavior must be executable truth — parse it and test it; distinguish SENT from HONORED explicitly; unified convenience keys must document their mapping table AND their precedence relative to escape-hatch keys.

**Probe:** `tests/models/test_model_settings_support.py` exists upstream and is cited BY the source as the enforcer (self-referential contract; read it directly when porting); `tests/test_settings.py` covers alias/value-level behavior.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ModelSettings Supported by TypedDict service_tier'
```

## Verdict
**Adopt** the parsed-docstring wire-contract pattern for any multi-backend settings type you own. **Adapt** bullet grammar to your test harness. **Omit** the provider tables themselves (vendor surface).
