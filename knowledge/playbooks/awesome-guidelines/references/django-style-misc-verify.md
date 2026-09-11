<!-- capsule-v2 -->
# Miscellaneous and verify — are strings marked for i18n and pre-commit gates clean?

**Source:** Django coding style §Miscellaneous, §Pre-commit. **Question:** Does the change meet Django hygiene, i18n, and contributor tooling expectations?

## i18n and hygiene seam
**Path/Symbol:** user-visible strings, module cleanliness.
**Signature:** gettext markers; no trailing WS; no inline author credits.
**Data Shape:** `_()`, `gettext_lazy` on UI strings; flake8-clean imports.

### Decisive pattern
```python
from django.utils.translation import gettext_lazy as _

label = _("Submit")
```

**Flow:** mark **all user-visible strings** for **i18n** per Django i18n docs → remove **unused imports** (flake8); `# NOQA` only for backwards-compat → strip **trailing whitespace** → don't embed **author names** in source — use **AUTHORS** file for attribution → remove gratuitous **"we"** in comments.
**Invariant:** hard-coded user-facing English without translation hook in reusable app fails i18n style review.
**Probe:** grep user strings in forms/models/views without `_(`; flake8 unused import warnings.

## Verify seam
**Flow:** install **pre-commit** hooks → on commit: **black**, **isort**, **flake8** (auto-fix where configured) → pair with project **EditorConfig** (4 Python / 2 HTML) → for apps: run **`python manage.py test`** on touched apps → template spot-check extends/spacing → model order audit on changed models.
**Probe:**
```bash
pre-commit run --all-files
python manage.py test app_name
```

**Invariant:** merging Django-style patch with pre-commit failures fails verify gate.
**Probe:** CI/pre-commit exit 0 on changed range.

## Verdict
i18n-ready strings, flake8-clean modules, pre-commit green, Django-specific template/model probes. Learning note: `django-style-learning-note.md`.
