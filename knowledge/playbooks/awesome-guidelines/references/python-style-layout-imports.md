<!-- capsule-v2 -->
# Layout and imports — does formatting and import style match project gates?

**Source:** PEP 8 §Code layout, §Imports; Google pyguide §2.2, §3.2, §3.13. **Question:** Will Ruff/Black/pylint pass and are import sources unambiguous?

## Layout seam
**Path/Symbol:** `*.py` module body.
**Signature:** 4-space indent; UTF-8; implicit line continuation inside `()[]{}`.
**Data Shape:** one statement per line; trailing commas on multiline collections.

### Decisive wrap
```python
income = (gross_wages
          + taxable_interest
          - ira_deduction)

with (
    open(path) as src,
    open(out, "w") as dst,
):
    dst.write(src.read())
```

**Flow:** prefer parentheses over backslash continuation → break before binary operators → keep docstrings/comments ≤72 when wrapping prose.
**Invariant:** no tab/space mix; no semicolon compound statements; line length follows **project** formatter (PEP 79 / Google 80 / Black 88 documented in pyproject).
**Probe:** `ruff check` / `black --check` / CI format job exit 0 on changed files.

## Import seam
```python
import os
import sys

from third_party import widgets

from myproject.package import module
```

**Flow:** group stdlib → third-party → local → absolute package paths (Google) → import **modules**, reference `module.symbol` in code.
**Invariant:** no ambiguous `import jodie` when `jodie.py` is local; no `from pkg import *`; typing/`collections.abc` may import symbols directly.
**Probe:** isort/ruff import rules clean; grep shows `from .* import [A-Z]` only in typing blocks or exempt modules.

## Verdict
Adopt 4-space implicit-wrap layout and grouped absolute imports; project formatter wins on column limit. Learning note: `python-style-learning-note.md`.
