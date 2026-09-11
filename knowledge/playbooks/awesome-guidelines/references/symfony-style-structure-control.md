<!-- capsule-v2 -->
# Structure and control flow — does PHP layout follow Symfony spacing, Yoda, and brace rules?

**Source:** Symfony coding standards §Structure. **Question:** Are comparisons, returns, class member order, and control flow Symfony-compliant?

## Structure seam
**Path/Symbol:** Symfony PHP classes — components, bundles, tests.
**Signature:** === + Yoda; trailing array commas; member order; no else-after-return.
**Data Shape:** promoted ctor one param per line; `new Foo()` always parenthesized.

### Decisive pattern
```php
if ('values' === $mergedOptions['some_default']) {
    return substr($dummy, 0, 5);
}

if (!$theSwitch) {
    return;
}

$this->qux->doFoo($value);
```

**Flow:** space after **commas**; spaces around **binary operators** except **concat `.`** → **identical comparison** `===` unless juggling required → **Yoda conditions** for literals (`'foo' === $var`) → **trailing comma** in multi-line arrays → blank line before **return** unless only statement in group → **`return null;`** vs **`return;`** for void → test methods: **no void return type** → **always braces** on control structures → **one class per file** → **extends/implements** on same line as class → order: **properties → public → protected → private** (ctor/setUp/tearDown first) → method args on **same line** as name except **promoted constructor** (one param/line + trailing comma) → **`new ClassName()`** always with parentheses → **no else/elseif/break** after branch that **returns/throws** → **no spaces** inside **`[` `]`** offset access → **`use`** for every non-global class → PHPDoc unions: **`null` last**.
**Invariant:** non-Yoda literal compare, else after return, or missing braces on single-line if body fails structure review.
**Probe:** php-cs-fixer dry-run; spot-check changed control flow.

## Verdict
Symfony spacing, Yoda identical compares, return discipline, and class/method layout. Learning note: `symfony-style-learning-note.md`.
