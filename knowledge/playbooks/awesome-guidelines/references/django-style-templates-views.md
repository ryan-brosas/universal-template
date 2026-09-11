<!-- capsule-v2 -->
# Templates and views — do DTL spacing and view signatures follow Django style?

**Source:** Django coding style §Template style, §View style. **Question:** Are templates spaced consistently and do views name the HttpRequest parameter `request`?

## Template seam
**Path/Symbol:** Django template language (`.html` templates).
**Signature:** extends first; spaced delimiters; named endblocks.
**Data Shape:** `{% extends %}` then `{% block content %}…{% endblock content %}`.

### Decisive pattern
```django
{% extends "base.html" %}

{% load humanize i18n l10n %}

{% block content %}
  <h1>{{ pages.title }}</h1>
  {% if user.name|lower == "admin" %}
    …
  {% endif %}
{% endblock content %}
```

**Flow:** **`{% extends %}`** first non-comment line — never after `{% load %}` → one space inside **`{{ user }}`** and **`{% load humanize %}`** → **`{% load %}`** libraries **alphabetical** → multiline blocks: **`{% endblock content %}`** with name → inside tags: spaces between tokens except around **`.`** and **`|`** → don't indent top-level **`{% block %}`** under extends.
**Invariant:** `{% load %}` before extends, `{{user}}`, or bare `{% endblock %}` on separate line fails template style review.
**Probe:** template lint or manual diff against rules; grep `{{[^ ]` in changed templates.

## View seam
**Flow:** view callables: first parameter **`request`**, not `req` or other alias.
**Invariant:** `def my_view(req, …)` fails view style review.
**Probe:** grep `def \w+\(req[^e]` on changed views.

## Verdict
DTL extends/spacing/endblock discipline and `request` as first view argument. Learning note: `django-style-learning-note.md`.
