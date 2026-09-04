<!-- capsule-v2 -->
# Instructions normalization pipeline — three-stage static/dynamic split with TemplateStr routing

## Source / Question
`pydantic_ai_slim/pydantic_ai/_instructions.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Agent instructions arrive as str | callable | TemplateStr | sequences | None, and toolsets ALSO emit instruction parts — how do you normalize all of it so static strings stay cheap and callables/templates resolve per-run without double-processing? A porter will isinstance-check `TemplateStr` explicitly and miss that it's callable (it lands in the wrong branch), or lose the dynamic flag on toolset parts.

## Path / Symbol
`_instructions.py` — `AgentInstructions` type alias (:12–18), `PreparedInstruction = str | SystemPromptRunner[AgentDepsT]` (:21), `normalize_instructions` (:24–32), `prepare_instructions` (:35–55), `normalize_toolset_instructions` (:58–76), `resolve_instructions` (:79–91).

## Signature
```python
def prepare_instructions(instructions) -> list[PreparedInstruction]:
    prepared = []
    for instruction in normalize_instructions(instructions):   # None→[], scalar→[x], seq→list
        if isinstance(instruction, str):
            prepared.append(instruction)                       # static: pass through unchanged
        else:
            prepared.append(_system_prompt.SystemPromptRunner(instruction))  # deferred
    return prepared

def normalize_toolset_instructions(result) -> list[InstructionPart]:
    if not result: return []
    items = [result] if isinstance(result, (str, InstructionPart)) else result
    parts = []
    for item in items:
        part = item if isinstance(item, InstructionPart) else InstructionPart(content=item, dynamic=True)
        if part.content.strip():                               # whitespace-only dropped
            parts.append(part)
    return parts
```

## Data Shape
Stage 1 `normalize`: flatten input (None → []; str-or-callable → single-element list; else list()). Stage 2 `prepare`: static strings pass through; EVERYTHING callable — including `TemplateStr`, deliberately NOT isinstance-branched — is wrapped in a `SystemPromptRunner` for later per-run invocation. Stage 3 `resolve`: run each prepared item against the RunContext, dropping None results. The toolset twin normalizes a toolset's `get_instructions` result into non-empty `InstructionPart`s where PLAIN STRINGS default to `dynamic=True` ("they come from an external/changeable source").

### Decisive source — the callable-branch comment (:51–53)
```python
# TemplateStr instances land here too: they are callable with a
# RunContext parameter, so SystemPromptRunner handles them like
# any other system prompt function.
```
And the shared-helper note on the toolset twin (:64–66): "Shared by `_agent_graph._get_instructions` and the deferred-capability loader's owned-toolset instruction collection so the two stay in sync" — one normalization function, two consumers, no drift.

**Flow:** constructor/run-time instructions → normalize → prepare (static vs runner) → at request build, resolve against RunContext; toolset parts join via the shared normalizer with dynamic-by-default semantics.

**Invariant:** Never branch on concrete string-subclasses you can enumerate — branch on BEHAVIOR (callable); keep static/dynamic classification in exactly one shared helper; empty/whitespace content is noise and must be dropped before it reaches prompts.

**Probe:** `tests/test_capabilities.py` deferred-capability instruction rendering asserts the exact hidden-capability prompt text (:2804–2809 snapshot); agent-level instruction behavior exercised across test_agent.py run snapshots.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'prepare_instructions normalize_toolset_instructions SystemPromptRunner'
```

## Verdict
**Adopt** the three-stage pipeline + behavior-based branching + shared toolset-part normalizer. **Adapt** the type union to your prompt types. **Omit** nothing.
