<!-- capsule-v2 -->
# Assets and verify — do YAML/Twig/CSS/JS match Drupal handbooks and CI gates pass?

**Source:** Drupal YAML, Twig, JS, CSS standards + GitLab CI templates. **Question:** Are config/templates/assets formatted correctly and verified by PHPCS/PHPStan/ESLint?

## Asset seam
**Path/Symbol:** `config/*.yml`, `templates/*.html.twig`, `js/*.js`, `css/*.css`.
**Signature:** 2-space YAML; Twig `@file` docblock; JS IIFE; PHPCS Drupal.
**Data Shape:** `my_module.settings.yml`; `{% if items %}`; `(() => { ... })();`.

### Decisive pattern
```yaml
# my_module.settings.yml
langcode: en
example:
  enabled: true
  label: 'Example'
```

```twig
{#
/**
 * @file
 * Default theme implementation for items.
 *
 * Available variables:
 * - items: List of item render arrays.
 */
#}
{% if items %}
  <ul{{ attributes.addClass('item-list') }}>
    {% for item in items %}
      <li>{{ item }}</li>
    {% endfor %}
  </ul>
{% endif %}
```

```javascript
/**
 * @file
 * Example behavior.
 */
(() => {
  Drupal.behaviors.example = (context) => {
    const $context = $(context);
    $context.find('.example').once('example').each(function attach() {
      // Behavior logic.
    });
  };
})();
```

**Flow:** **YAML** — filename **`extension.name.yml`**; simple config prefixed with **module/theme machine name**; **2-space** indent; `#` comments sparingly → **Twig** — file docblock in `{# #}` matching PHP template docs; **`{% if var %}`** without redundant `is defined` for normal emptiness; when printing individual HTML attrs still include full **`{{ attributes }}`** at tag end → **JS** — entire file in **closure/IIFE**; **`Drupal.behaviors`**; **semicolons** required; **lowerCamelCase** vars; jQuery vars prefixed **`$`**; **no globals**; ESLint **eslint-config-airbnb** → **CSS** — **2-space**; LF endings; file header comment; ruleset docblocks for non-obvious blocks → **verify**: **PHPCS** with Drupal standard on PHP; **PHPStan** at project level; **ESLint** on JS; **stylelint** where configured; accessibility per `wcag-accessibility-practices` for UI changes.
**Invariant:** unprefixed config yml name, Twig missing attributes merge, global JS var, or PHPCS error on changed PHP fails asset/verify gate.
**Probe:** `phpcs --standard=Drupal`; `phpstan analyse` on src/; eslint on changed `.js`.

## Verdict
Drupal-shaped YAML/Twig/JS/CSS plus PHPCS, PHPStan, and ESLint verification. Learning note: `drupal-style-learning-note.md`.
