<!-- capsule-v2 -->
# Python formatting and imports — does Django Python match black, PEP 8, and isort group rules?

**Source:** Django coding style §Pre-commit, §Python style, §Imports. **Question:** Is Python formatted with black/isort and are imports grouped per Django contributor standards?

## Python seam
**Path/Symbol:** Django app `.py` modules, tests.
**Signature:** black 88; snake_case; f-string readability rules.
**Data Shape:** pre-commit hooks; EditorConfig 4-space.

### Decisive pattern
```python
def poll_get_unique_voters(poll):
    user = poll.owner
    return f"hello {user.name}"


class PollForm(forms.Form):
    ...
```

**Flow:** run **pre-commit** (black, isort, flake8) → format with **black** (88 cols code; **79** for comments/docstrings) → follow **PEP 8** respecting surrounding code → **snake_case** variables/functions; **InitialCaps** classes → **f-strings**: only simple property access — assign **locals** for calls/math; **never f-strings** for translatable user/log strings → tests: **`assertRaisesMessage`**, **`assertIs(True/False)`**; test docstrings state **expected behavior** without "Tests that…".
**Invariant:** camelCase identifiers, complex f-string expressions, or assertTrue on booleans fails Django Python style review.
**Probe:** pre-commit run; black --check; flake8 on changed paths.

## Import seam
**Flow:** **isort** groups: future → stdlib → third-party → Django → local → try/except → within group: `import module` before `from`, alphabetical, uppercase names before lowercase → **absolute** django imports; **one-dot** relative for local app → **convenience imports** (`from django.views import View`) → long imports: parentheses, trailing comma, 4-space indent → one blank line after imports; two before first class/function → `# isort:skip` only for circular imports.
**Invariant:** multi-dot relative import or deep convenience path when shallow exists fails import review.
**Probe:** isort --check-only; import block spot review on new modules.

## Verdict
black/isort/flake8 Python with Django import grouping and test assertion idioms. Learning note: `django-style-learning-note.md`.
