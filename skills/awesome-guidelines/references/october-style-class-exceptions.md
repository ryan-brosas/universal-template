<!-- capsule-v2 -->
# Classes and exceptions — are extensions protected-friendly and errors use Rain exception types?

**Source:** Developer Guide §Class guidance + Available exceptions. **Question:** Do classes favor extension and throw the correct October exception for user vs system failures?

## Class seam
**Path/Symbol:** Plugin classes, boot/init error handlers.
**Signature:** protected members; ApplicationException user errors.
**Data Shape:** `throw new ApplicationException('You must sign in.');`.

### Decisive pattern
```php
<?php

namespace Acme\Blog\Classes;

use ApplicationException;
use SystemException;

class PostPublisher
{
    protected array $channels = [];

    public function publish(array $data): void
    {
        if (empty($data['title'])) {
            throw new ApplicationException('Please enter a title.');
        }

        try {
            $this->sendToApi($data);
        } catch (\Throwable $e) {
            throw new SystemException('Unable to contact the publishing API.');
        }
    }
}
```

**Flow:** prefer **`protected`** over **`private`** so classes can serve as base classes → **scalar values**: **`public` property** acceptable vs getter/setter boilerplate → **collections**: **`protected` array** with **`getX` / `setX`** helpers → user-facing failures → **`ApplicationException`** (safe message, no file/line leak) → critical/system failures → **`SystemException`** (logged with detail) → form field errors → **`ValidationException`** with field => message map → missing records → **`NotFoundException`** → register custom **`App::error` handlers** in plugin **`boot()`** or **`init.php`** → model chain scopes prefixed **`apply`** (e.g. `scopeApplyUser`).
**Invariant:** private extension base class, generic `\Exception` for user message, or SystemException for simple validation text fails class/exception review.
**Probe:** grep `throw new \\Exception` in plugin; visibility scan on intended base classes.

## Verdict
Extension-friendly visibility with Rain exception taxonomy and boot-time handler registration. Learning note: `october-style-learning-note.md`.
