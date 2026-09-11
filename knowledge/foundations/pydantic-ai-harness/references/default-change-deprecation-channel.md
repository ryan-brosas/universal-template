<!-- capsule-v2 -->
# Scope default migration: behavior-changing defaults warn ONCE per instance, with restore-and-keep escape hatches

## Source / Question
`pydantic_ai_harness/conversation_search/_capability.py` (drift +93L) + `_warn.py` @ `main@f971198` — `ConversationSearch.scope` moved from `'all'` to `'conversation'`: existing callers keep working but silently get a NARROWER corpus. How do you announce a silent default change without spamming, while keeping both values fully supported?

## Path / Symbol
`_warn.py` — `warn_default_changed(*, owner, option, old, new, impact, stacklevel=4)` (new sibling of `warn_renamed`); `_capability.py` — `scope: SearchScope | None = None` tri-state (:None=caller-didn't-choose), `effective_scope` resolves None→'conversation' + warns once per instance, scope-conditional instruction variants (`_CONVERSATION_INSTRUCTIONS` vs `_ALL_INSTRUCTIONS`, the latter deliberately NOT naming the conversation boundary "would talk the model out of the cross-conversation recall that opting into `all` exists to enable").

## Signature
```python
def warn_default_changed(*, owner: str, option: str, old: str, new: str, impact: str, stacklevel: int = 4):
    warnings.warn(
        f'`{owner}` now defaults to `{option}={new!r}`; it previously defaulted to `{option}={old!r}`. '
        f'{impact} '
        f"Pass `{option}={old!r}` to restore the previous behavior, or `{option}={new!r}` to keep "
        f'the new one and silence this warning.',
        category=HarnessDeprecationWarning, stacklevel=stacklevel)   # default targets dataclass __post_init__ caller
```

## Data Shape
Tri-state field (`None` sentinel) is what makes once-per-instance possible: an explicit value never warns; `effective_scope` carries the resolved value so downstream logic never re-derives it. The toolset's own default moved too and announces identically.

### Decisive source
Warning contract (:docstring): "Call this only when the caller left the option unset, so an explicit choice of either value stays silent, and call it once per construction rather than per use." Migration honesty (:capability docstring): "Upgrading raises nothing — a store-wide caller keeps working with a narrower corpus — so leaving `scope` unset emits a `HarnessDeprecationWarning` once per instance… both are supported and neither is deprecated." Fail-closed scoping preserved from pass 3: conversation-scope run WITHOUT conversation_id searches NOTHING.

**Flow:** construct with unset scope → resolve to new default → emit one HarnessDeprecationWarning naming old/new/restore/keep → subsequent toolset/instruction calls silent.
**Invariant:** explicit old OR new ⇒ zero warnings; exactly ONE warning per instance regardless of how many toolsets/instructions are built; message always contains the machine-greppable restore and keep spellings.

## Probe (direct test)
`tests/conversation_search/test_conversation_search.py::test_unset_scope_resolves_to_conversation_and_warns` (:628, asserts resolved value + both spellings in message), `test_unset_scope_warns_once_per_instance` (:640, three toolset builds + instructions ⇒ len(record)==1), `test_unset_toolset_scope_warns` (:652), `test_explicit_scope_never_warns` (:660).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'warn_default_changed effective_scope'
```

## Verdict
**Adopt** the tri-state + once-per-instance + restore/keep-message pattern for ANY behavior-changing default in a library. **Adopt** instruction variants that don't undermine the opt-in mode. **Omit** nothing.
