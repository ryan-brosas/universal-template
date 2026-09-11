<!-- capsule-v2 -->
# Model display label — pure function over hyphen-split parts with digit-run decimal joining

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/_abstract.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Every model identity needs a human-friendly display label for UIs and telemetry — how do you derive `claude-sonnet-4-5 → "Claude Sonnet 4.5"` and `gpt-5 → "GPT 5"` from a bare model name with no lookup table? A porter will special-case vendor names or mangle version runs like `2.5` into `2 5`.

## Path / Symbol
`models/_abstract.py` — `AbstractModel.label` (:50–77), `model_id` (:45–48), `base_url` (:40–43), `system` (:28–38), `__aenter__/__aexit__` (:79–90).

## Signature
```python
@property
def label(self) -> str: ...
@property
def model_id(self) -> str:   # 'provider:model_name' fully-qualified form
    return f'{self.system}:{self.model_name}'
```

## Data Shape
`AbstractModel` is the identity shared by request-response AND realtime models (kept apart from `models/__init__.py` because realtime models need the same name/provider/label trio for resolution and OTel attributes). `system` feeds the `gen_ai.system` semantic-convention attribute and should use well-known OTel values when applicable. `base_url` defaults None; async context-manager defaults are pass-through (`test_model.py:493` pins `await AbstractModel.__aenter__(model) is model`).

### Decisive source — the four-rule part walk (:60–77)
```python
label = self.model_name
if '/' in label:
    label = label.split('/')[-1]          # OpenRouter style: meta-llama/llama-3-70b -> llama-3-70b
parts = label.split('-')
result: list[str] = []
for i, part in enumerate(parts):
    if i == 0 and part.lower() == 'gpt':
        result.append(part.upper())       # leading gpt -> GPT (only position 0)
    elif part.replace('.', '').isdigit():
        if result and result[-1].replace('.', '').isdigit():
            result[-1] = f'{result[-1]}.{part}'   # adjacent digit run JOINS with a dot: 4 + 5 -> 4.5
        else:
            result.append(part)
    else:
        result.append(part.capitalize())
return ' '.join(result)
```
Docstring-pinned examples: `gpt-5 → GPT 5`, `claude-sonnet-4-5 → Claude Sonnet 4.5`, `gemini-2.5-pro → Gemini 2.5 Pro`, `meta-llama/llama-3-70b → Llama 3 70b`.

**Flow:** strip vendor path prefix → split on hyphens → walk once: uppercase a LEADING `gpt`, merge consecutive numeric tokens with `.`, capitalize everything else → single-space join.

**Invariant:** Pure function of `model_name` — no network, no registry; digit adjacency is the ONLY joining rule, so `3-70b` stays two tokens ("Llama 3 70b") because `70b` is not all digits.

**Probe:** No direct unit test at this HEAD — behavior is pinned transitively via `tests/models/test_model.py::test_infer_model` (:234, asserting `m.model_id == f'{expected_system}:{expected_model_name}'`) and every model cassette's OTel attribute assertions; treat the docstring examples as the contract and re-pin if upstream ships `test_label`.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'AbstractModel label model_id system base_url'
```

## Verdict
**Adopt** the pure derivation verbatim as a util; it needs no other machinery. **Adapt** nothing — the rules are complete. **Omit** the ABC plumbing if your host has its own model interface.
