# Django coding style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `django-style-*.md` capsules, `django-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Django coding style](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/) (primary) | Python black/PEP8, imports, templates, views, models, settings laziness, i18n, pre-commit |
| Django `coding-style.txt` in django/django (primary mirror) | Full normative text for templates, model ordering, choices enums |
| `python-coding-practices` (secondary) | Generic PEP 8/Google — Django adds 88-col black, import groups, Django-specific tests |
| `django-foundation` (secondary) | Framework patterns — this skill is **style/conventions** for Django code review |

**Scope:** **Django project and app code** (Python, templates, contributing-style tests). **Not:** full ORM architecture (`django-foundation`). **JS in Django admin:** see linked Django JS style doc — out of scope unless admin JS patch.

## Mental model

Django style is **black-formatted Python + grouped imports + template whitespace discipline + ordered models**:

1. **Python** — black (88 cols code, 79 docs); snake_case; f-string readability rules; test assertions.
2. **Imports** — isort groups; absolute Django imports; one-dot relative local; convenience imports.
3. **Templates & views** — `{% extends %}` first; spaced `{{ }}`/`{% %}`; named `endblock`; first arg `request`.
4. **Models & settings** — field order; Meta after fields; TextChoices; lazy settings access.
5. **Misc & verify** — i18n all strings; pre-commit; flake8/isort; no author names in code.

## Decision tables

### Pre-commit & Python

| Topic | Rule |
|---|---|
| Hooks | pre-commit with black, isort, flake8 |
| Format | black; EditorConfig 4 spaces Python, 2 HTML |
| Line length | 88 code; 79 comments/docstrings |
| PEP 8 | Follow except black line length; respect surrounding style |
| f-strings | Plain attr access only; assign locals for complex; no f-strings for translatable strings |
| Naming | snake_case funcs/vars; InitialCaps classes |
| Comments | Avoid "we" in comments |
| Tests | assertRaisesMessage; assertIs(True/False); docstring states expected behavior |

### Imports

| Group order | future → stdlib → third-party → Django → local → try/except |
|---|---|
| Style | `import module` before `from module import`; alphabetical; uppercase before lowercase on line |
| Django | absolute for django.*; `from .foo import Bar` one-dot local only |
| Long imports | parens + trailing comma; 4-space indent continuations |
| Convenience | `from django.views import View` not deep path |
| Skip | `# isort:skip` for circular imports |

### Templates

| Topic | Rule |
|---|---|
| extends | First non-comment line |
| spacing | One space inside `{{ }}` and `{% %}` |
| load | Alphabetical library list |
| endblock | Name on endblock when multiline: `{% endblock content %}` |
| filters | No spaces around `.` and `\|`; spaces elsewhere in `{% if %}` |
| blocks | Don't indent top-level blocks under extends |

### Views

| Topic | Rule |
|---|---|
| First param | Always `request` not `req` |

### Models

| Topic | Rule |
|---|---|
| Fields | lowercase_with_underscores |
| Meta | After fields; blank line before Meta |
| Order | fields → managers → Meta → `__str__` → save → get_absolute_url → custom methods |
| choices | UPPER constants + CHOICES dict or TextChoices enum |

### Settings

| Topic | Rule |
|---|---|
| Top-level access | Don't read `settings.FOO` at import time in reusable modules |
| Pattern | LazyObject, lazy(), or lambda deferral |

### Miscellaneous

| Topic | Rule |
|---|---|
| i18n | Mark strings for translation |
| Imports | Remove unused; `# NOQA` only for compat |
| Whitespace | No trailing WS |
| Attribution | Names in AUTHORS not inline in code |

## Anti-patterns

- Manual formatting fighting black
- 79-char black fights in Python code
- f-strings with calls/expressions inside braces
- f-strings for user-visible translatable messages
- camelCase model fields
- Meta class before fields
- Multi-dot relative imports
- `{% load %}` before `{% extends %}`
- `{{user}}` no spaces
- Unnamed `{% endblock %}` on separate line
- View first parameter named `req`
- `settings.X` evaluated at module import in pluggable app
- User-facing string without gettext wrapper
- Author name comments in source files

## Skill trace

| Artifact | Role |
|---|---|
| `django-style-python-imports.md` | black, PEP8, imports, tests |
| `django-style-templates-views.md` | DTL + view signature |
| `django-style-models-settings.md` | models, choices, lazy settings |
| `django-style-misc-verify.md` | i18n, hygiene, pre-commit |
| `django-coding-practices/SKILL.md` | Django style review workflow |

## Relation to sibling skills

| Django style | python-coding-practices |
|---|---|
| black 88 / isort groups | ruff/black generic |
| Template/view/model rules | N/A |
| assertRaisesMessage | general exception idioms |
| Lazy settings | import-time side effects |

App architecture: `django-foundation`.
