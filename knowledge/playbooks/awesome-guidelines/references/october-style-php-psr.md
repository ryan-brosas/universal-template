<!-- capsule-v2 -->
# PHP and PSR — does October code follow PSR-1/2/4 with camelCase and documented carve-outs?

**Source:** Developer Guide §Exceptions to PSR + october repo README. **Question:** Is PHP PSR-compliant except for allowed October AJAX and control-flow layout preferences?

## PHP seam
**Path/Symbol:** Plugin PHP — models, controllers, components.
**Signature:** PSR-1/2/4; camelCase vars; snake_case DB/lang/HTML keys.
**Data Shape:** `$firstName`; `$model->is_visible`; `index_onSave()`.

### Decisive pattern
```php
<?php

namespace Acme\Blog\Controllers;

class Posts
{
    public function index()
    {
        $recordCount = $this->vars['recordCount'] ?? 0;
        $this->page['posts'] = $this->listPosts($recordCount);
    }

    public function index_onPublish()
    {
        // AJAX handler scoped to index action.
    }

    public function onRefresh()
    {
        // Global AJAX handler.
    }
}
```

**Flow:** follow **PSR-1**, **PSR-2**, **PSR-4** as October baseline → **camelCase** for PHP variables and methods → **snake_case** for database model attributes/relationships, postback parameters, HTML element names, and **language keys** → backend controller **AJAX handlers** may use a **single underscore**: `{action}_onHandler()` or global `onHandler()` — PSR-2 camelCase exception → prefer **`elseif` / `catch` blocks on new lines** after closing `}` (October spacing preference; document PHPCS exception if needed) → view templates use **`.htm`** extension only.
**Invariant:** snake_case PHP variable in non-DB code, invalid AJAX naming pattern, or non-`.htm` view extension fails October PHP/PSR review.
**Probe:** PHPCS PSR-2 on plugin PHP; grep `$[a-z]+_[a-z]` outside models/lang keys.

## Verdict
PSR-based October PHP with camelCase/snake_case split and controller AJAX underscore exception. Learning note: `october-style-learning-note.md`.
