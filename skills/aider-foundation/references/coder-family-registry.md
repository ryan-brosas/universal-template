<!-- capsule-v2 -->
# Coder-family registry — edit_format as the class discriminator with dynamic argparse choices

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you wire 13 coder variants into one factory + CLI validation without a hand-maintained format list drifting from the classes?

## `__all__` IS the registry; argparse choices are derived from it at parser-build time
**Path/Symbol:** `aider/coders/__init__.py` (:1-34, imports 13 coders; `SingleWholeFileFunctionCoder` deliberately commented out); factory `aider/coders/base_coder.py::Coder.create(...)` dispatches on edit_format; consumer `aider/args.py` :48 set-comprehension + :167 `choices=edit_format_choices`.
**Signature:** each subclass declares `edit_format = "<name>"` (e.g. `"whole"`, `"diff"`, `"diff-fenced"`, `"context"`, editor twins `"editor-diff"`, `"editor-whole"`, `"editor-diff-fenced"`); help/help-ask have NO edit_format (None) so they're excluded from choices.
**Data Shape:** `edit_format_choices = sorted({c.edit_format for c in _aider_coders.__all__ if hasattr(c, "edit_format") and c.edit_format is not None})`.

### Decisive source
```python
# aider/coders/__init__.py
from .architect_coder import ArchitectCoder
...
__all__ = [HelpCoder, AskCoder, Coder, EditBlockCoder, EditBlockFencedCoder,
           WholeFileCoder, PatchCoder, UnifiedDiffCoder, UnifiedDiffSimpleCoder,
           ArchitectCoder, EditorEditBlockCoder, EditorWholeFileCoder,
           EditorDiffFencedCoder, ContextCoder]

# aider/args.py — list stays in sync if new formats are added:
from aider import coders as _aider_coders
edit_format_choices = sorted(
    {c.edit_format for c in _aider_coders.__all__ ...}
)
```

**Flow:** `--edit-format X` validates against the derived set → `Coder.create(main_model=..., edit_format=X, from_coder=...)` resolves the class (explicit format > model-preference > base default) → thin subclasses (EditBlockFencedCoder = EditBlockCoder + different prompts/fence; EditorWholeFileCoder = WholeFileCoder + editor prompts) reuse parent parsers verbatim.
**Invariant:** adding a new coder = one class file + one `__init__` import/export; CLI help (:167 choices), shtab completion, and factory routing all update automatically — there is no second list to forget.
**Probe:** deterministic anchors: `grep -nF 'edit_format_choices' aider/args.py | head -2` → :48 comprehension + :167 choices use. Direct tests: `tests/basic/test_coder.py::test_allowed_to_edit` family executed GREEN this run via repo venv (`python -m pytest tests/basic/test_coder.py -q`: **42 passed, 29 subtests**).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "EditBlockFunctionCoder", limit: 3 });
// rank-1: editblock_func_coder.EditBlockFunctionCoder.__init__ (the DEPRECATED twin kept out of __all__)
```

## Verdict
Adopt the registry-as-module pattern verbatim; note the deprecated function-call coder (`editblock_func_coder.py`) raises RuntimeError in `__init__` and is excluded from `__all__` — keep such fossils OUT of the registry rather than behind flags.
