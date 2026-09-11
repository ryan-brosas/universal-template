<!-- capsule-v2 -->
# Models and settings — are fields ordered, choices idiomatic, and settings access lazy?

**Source:** Django coding style §Model style, §Use of django.conf.settings. **Question:** Do models follow Django field/Meta ordering and avoid import-time settings reads?

## Model seam
**Path/Symbol:** `models.Model` subclasses in Django apps.
**Signature:** snake_case fields; Meta after fields; TextChoices.
**Data Shape:** fields → managers → Meta → magic methods → save → URL → custom.

### Decisive pattern
```python
class MyModel(models.Model):
    DIRECTION_UP = "U"
    DIRECTION_DOWN = "D"
    DIRECTION_CHOICES = {
        DIRECTION_UP: "Up",
        DIRECTION_DOWN: "Down",
    }

    direction = models.CharField(max_length=1, choices=DIRECTION_CHOICES)
    first_name = models.CharField(max_length=20)

    class Meta:
        verbose_name_plural = "people"

    def __str__(self):
        return self.first_name
```

**Flow:** field names **lowercase_with_underscores** — no camelCase → **`class Meta`** after all fields with **blank line** separator → inner order: **fields → custom managers → Meta → `__str__`/magic → `save` → `get_absolute_url` → custom methods** → **choices**: UPPER constant keys + `FOO_CHOICES` dict **or** nested **`TextChoices`/`IntegerChoices`** enum.
**Invariant:** Meta before fields, camelCase field names, or inline string choices without constants fails model style review.
**Probe:** model class structure review; grep `class Meta` position vs fields.

## Settings seam
**Flow:** reusable modules must **not** read **`django.conf.settings`** at **import time** (breaks manual `settings.configure`) → defer with **`LazyObject`**, **`lazy()`**, or **`lambda`** until runtime.
**Invariant:** `foo = get_callable(settings.FOO_VIEW)` at module top level in pluggable app fails settings review.
**Probe:** grep `from django.conf import settings` + top-level settings attr access outside settings module.

## Verdict
Ordered models with idiomatic choices and lazy settings access in shared modules. Learning note: `django-style-learning-note.md`.
