<!-- capsule-v2 -->
# _StrictABCMeta — why do half-implemented evaluator subclasses fail at class-definition time instead of instantiation?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When porting an evaluator framework, how do you make forgetting to implement `evaluate` an error at subclass-definition time while still allowing intentional new abstract layers?

## Definition-time abstract-method enforcement metaclass
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/_base.py:_StrictABCMeta` (:19-39) applied via `BaseEvaluator(metaclass=_StrictABCMeta)` (:42-43).
**Signature:** `__new__(mcls, name, bases, namespace, /, **kwargs) -> type`.
**Data Shape:** Standard ABCMeta machinery; inspects `result.__abstractmethods__` (frozenset produced by ABCMeta) against `namespace` keys of the class being defined.

### Decisive source
```python
is_proper_subclass = any(isinstance(c, _StrictABCMeta) for c in result.__mro__[1:])
if is_proper_subclass and result.__abstractmethods__:
    # Only error on abstract methods inherited from a parent but not implemented.
    # Methods defined in this class's own namespace are intentionally abstract (new abstract layer).
    own_abstracts = frozenset(m for m in result.__abstractmethods__ if m in namespace)
    inherited_unimplemented = result.__abstractmethods__ - own_abstracts
    if inherited_unimplemented:
        raise TypeError(f'{name} must implement all abstract methods: {abstractmethods}')
```

**Flow:** class body executes → `ABCMeta.__new__` computes `__abstractmethods__` → metaclass splits that set into methods *declared abstract in this very class* (`own_abstracts`) vs everything else → if any inherited-but-unimplemented method remains, raise `TypeError` immediately; otherwise return the class.
**Invariant:** The "own namespace" carve-out is load-bearing: `Evaluator` and `ReportEvaluator` themselves declare `@abstractmethod evaluate`, which standard ABCMeta permits as an intermediate abstract class. Without subtracting `own_abstracts`, defining those two base classes would itself raise. A porter who copies only the error branch breaks the framework's own root classes.
**Probe:** `tests/evals/test_evaluator_base.py::test_strict_abc_meta` (:78-110) — `class InvalidEvaluator(Evaluator): pass` raises `TypeError` matching `must implement all abstract methods.*'evaluate'`, a `PartialAbstract` adding a second unimplemented abstract also raises, and `Evaluator`/`ReportEvaluator` still expose `'evaluate'` in their own `__abstractmethods__`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"_StrictABCMeta","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `_base.py 28-39` (method) and `19-39` (class).

## Verdict
Adopt the metaclass verbatim — it is 20 lines with zero pydantic-ai coupling and converts a runtime surprise ("my evaluator list silently skipped instantiation") into an import-time error. Adapt the error message wording to your host's conventions. Omit nothing. Direct test executed GREEN at pin (suite `test_evaluator_base.py`, 18 passed).
