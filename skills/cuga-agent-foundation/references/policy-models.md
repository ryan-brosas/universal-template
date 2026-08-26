<!-- capsule-v2 -->
# Policy Models — how do six policy types share one trigger system without misrouting matches?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you model heterogeneous agent-governance policies (guide / block / approve / format) over one trigger vocabulary so a trigger authored for one policy type can never silently evaluate against the wrong state field?

## Discriminated union + target-coercing validators
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/models.py` (`PolicyType` :9-17, `PolicyActionType` :20-31, triggers :54-126, `Playbook.validate_trigger_targets` :155-174, `IntentGuard.validate_trigger_targets` :223-242, `ToolGuide` :245-277, `ToolApproval` :279-307, `OutputFormatter.validate_trigger_targets` :338-357, `PolicyDecision` :405-420).

**Signature:** `Trigger = Union[NaturalLanguageTrigger, KeywordTrigger, AppTrigger, StateTrigger, ToolTrigger, AlwaysTrigger]`; each policy is a pydantic BaseModel with `type: Literal[PolicyType.X]` and `triggers: List[Trigger]`.

**Data Shape:** Triggers carry a `target` naming which context field to evaluate (`intent`, `chat_messages`, `sub_task`, `agent_response`, default `"intent"`); NL adds `threshold: float = 0.7 ge=0 le=1`; keyword adds `case_sensitive=False` and `operator: Literal["and","or"]="and"`. Every policy has `priority: int = 0` (higher wins) and `enabled: bool = True`.

### Decisive source
```python
# models.py:338-357 — OutputFormatter rewrites any NL/keyword trigger whose
# target isn't exactly "agent_response". Playbook/IntentGuard do the same
# coercion toward "intent". Authoring mistakes are repaired, not rejected.
@model_validator(mode='after')
def validate_trigger_targets(self):
    updated_triggers = []
    for trigger in self.triggers:
        if isinstance(trigger, (NaturalLanguageTrigger, KeywordTrigger)):
            if not trigger.target or trigger.target != "agent_response":
                trigger_dict = trigger.model_dump()
                trigger_dict['target'] = "agent_response"
                ...  # rebuilt trigger replaces the original in self.triggers
```
And the ToolApproval docstring pins its unusual stage (`models.py:282-284`):
> "ToolApproval policies are checked AFTER code generation, not during initial policy matching. They check if the generated code uses any of the specified tools/apps."

**Flow:** author JSON/py dict → pydantic validates into the discriminated union → per-type validator normalizes trigger targets → storage persists → matchers later call `context.get_target_text(trigger.target)` trusting the normalized field.

**Invariant:** A porter who skips the coercion will route formatter triggers against `intent` (they'd fire on every request) or playbook triggers against `agent_response` (they'd never fire). The coercion direction is: Playbook/IntentGuard ⇒ `intent`; OutputFormatter ⇒ `agent_response`; ToolGuide/ToolApproval keep their declared targets because they match on tool/app fields instead.

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_e2e_output_formatter.py` — every e2e case builds formatters with plain keyword/NL triggers (no explicit target) and still matches only on the final AI message; `test_e2e_output_formatter.py:34 test_e2e_output_formatter_with_keyword_trigger`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "validate_trigger_targets OutputFormatter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the discriminated-union policy model plus after-validation target coercion and the stage annotations (ToolApproval = post-codegen, OutputFormatter = post-answer). Adapt field names/threshold defaults to host. Omit CustomPolicy's free-form action_config unless you need an extension hook.
