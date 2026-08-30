---
name: django-coding-practices
description: "Use when authoring or reviewing Django code — black/isort imports, DTL spacing, request-first views, model field order, TextChoices, lazy settings, i18n strings, and pre-commit verification."
disable-model-invocation: true
---

# Django Coding Practices

Application skill for Django official coding style ingest (`awesome-guidelines`). Generic Python: `python-coding-practices`. Framework architecture: `django-foundation`.

## Core Principle

Django code reads as **one codebase** — black-formatted Python, isort import groups, disciplined templates, ordered models, lazy settings in reusable modules, and i18n-ready strings verified by pre-commit.

## When to Use / NOT

- Django apps: models, views, forms, templates, tests.
- Contributing to or mirroring django/django conventions in private projects.
- Setting up pre-commit for Django repos.

**NOT when:**

- Non-Django Python — `python-coding-practices`.
- ORM/query design, middleware architecture — `django-foundation`.
- Django admin JavaScript — Django JS style doc (separate).

## Workflow

1. **Python/imports** — black, isort, tests (`django-style-python-imports.md`).
2. **Templates/views** — DTL + `request` (`django-style-templates-views.md`).
3. **Models/settings** — field order, choices, lazy settings (`django-style-models-settings.md`).
4. **Misc/verify** — i18n, hygiene, pre-commit (`django-style-misc-verify.md`).

## Red Flags

- Unformatted or non-black Python in Django app
- f-strings for translatable user messages
- Complex expressions inside f-string braces
- camelCase model fields or methods
- Meta class before model fields
- Multi-dot relative imports
- Deep import when convenience import exists
- `{% load %}` before `{% extends %}`
- `{{user}}` or `{%tag%}` spacing violations
- Unnamed `{% endblock %}` on its own line
- View first parameter not named `request`
- Import-time `settings.FOO` in reusable module
- User-visible strings without gettext
- Author name in source file header
- Trailing whitespace in patches
- pre-commit/flake8 failures on changed files

## Verification

- `pre-commit run` on changed files (black, isort, flake8)
- `python manage.py test` for touched apps
- Template extends/spacing manual or linter check
- Model structure checklist on changed models
- i18n grep on new user-facing strings

## Skill Result Contract

```xml
<skill_result>
  <skill>django-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>diff, pre-commit output, test log</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>import-time settings, i18n miss, or DTL spacing drift</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/django-style-learning-note.md`
- `awesome-guidelines/references/django-style-python-imports.md`
- `awesome-guidelines/references/django-style-templates-views.md`
- `awesome-guidelines/references/django-style-models-settings.md`
- `awesome-guidelines/references/django-style-misc-verify.md`

## Related skills

- `python-coding-practices` — PEP 8/Google baseline
- `django-foundation` — Django framework patterns
- `frontend-markup-practices` — non-DTL HTML/CSS
