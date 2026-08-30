<!-- capsule-v2 -->
# Formatting and layout — does code match community Ruby mechanical rules?

**Source:** Ruby Style Guide §Source Code Layout; Airbnb §Whitespace. **Question:** Will RuboCop layout cops pass on changed files?

## Layout seam
**Path/Symbol:** `*.rb` source files.
**Signature:** 2-space indent; UTF-8; Unix LF; trailing newline; no semicolons.
**Data Shape:** 80-column default (project may allow 100–120 consistently).

### Decisive pattern
```ruby
# frozen_string_literal: true

class InvoiceService
  MAX_RETRIES = 3

  def initialize(repository:)
    @repository = repository
  end

  def call(account_id)
    return if account_id.nil?

    @repository.find(account_id)
  end
end
```

**Flow:** editor soft tabs at 2 → wrap near 80 → one expression per line → file ends with newline.
**Invariant:** hard tabs never used; no `puts 'a'; puts 'b'` on one line.
**Probe:** `rubocop --only Layout` (or project config) exit 0 on diff; `cat -A` shows no `^I` tabs.

## Spacing seam
```ruby
sum = 1 + 2
a, b = 1, 2
class FooError < StandardError; end

{ one: 1, two: 2 }
foo&.bar
!ready?
```

**Flow:** spaces around operators and after commas/colons → no space after `!`/`(` in calls → safe navigation `&.` over manual nil checks.
**Invariant:** `sum=1+2` and `num.+ 42` are review rejects.
**Probe:** Layout/Space cops clean; grep shows no `&& foo && foo.` chains where `&.` applies.

## Blank-line seam
```ruby
class Person
  def public_method
  end

  private

  def private_method
  end
end
```

**Flow:** one blank line between methods → blank line before/after `private`/`protected` → no consecutive empty lines.
**Invariant:** access modifiers indented with class body; modifier preceded and followed by blank line.
**Probe:** Layout/EmptyLines cops; visual scan shows modifier separation.

## Verdict
Adopt 2-space UTF-8 layout with operator spacing and safe navigation. Learning note: `ruby-style-learning-note.md`.
