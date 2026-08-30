<!-- capsule-v2 -->
# Methods and control flow — are defs, calls, and booleans idiomatic?

**Source:** Ruby Style Guide §Methods, §and/or; Airbnb §Methods, §Conditional Expressions. **Question:** Will method signatures and boolean logic read without precedence surprises?

## Definition seam
**Path/Symbol:** instance/class methods in application code.
**Signature:** keyword parameters; parentheses when args present.
**Data Shape:** short methods (≤10 LOC target); no top-level defs outside scripts.

### Decisive pattern
```ruby
class Exporter
  def export(rows, format: :csv, at: Time.now)
    build(rows, format: format, at: at)
  end

  def build(rows, format:, at:)
    Formatter.for(format).render(rows, generated_at: at)
  end
end
```

**Flow:** prefer keyword args over positional defaults → `def foo` without parens when no args → `def foo(x)` with parens when args → use `def self.method` for singleton methods.
**Invariant:** `def obliterate(a, gently = true)` positional defaults fail review; `def SomeClass.method` rejected.
**Probe:** Style/OptionalArguments cop; no new top-level `def` outside `bin/`/`script/`.

## Call seam
```ruby
user = User.find_by(id: 42)
Person.new('Ada', 36)
fork
collection.empty?

render(partial: 'shared/header')
```

**Flow:** parentheses when passing arguments or receiving a value → omit when zero-arg → no space before `(` in calls.
**Invariant:** `User.find_by id: 1` and `nil?()` fail review.
**Probe:** Style/MethodCallWithoutArgsParentheses / Parentheses cops per project config.

## Boolean and flow seam
```ruby
if valid? && authorized?
  process
end

args = extract_arguments or raise ArgumentError, 'missing args'
suspended? and return :denied
```

**Flow:** `&&`/`||` inside conditions and boolean expressions → `and`/`or` only for control-flow sequences (raise/early return) → avoid stacking multiple flow operators in one line.
**Invariant:** `if a and b` and `ok = a and b` are review rejects.
**Probe:** Lint/AndOr cop; no modifier `rescue` for flow (`read rescue nil`).

## Endless methods (Ruby 3+)
```ruby
def the_answer = 42

def square(x) = x * x
```

**Flow:** endless form only for single-expression, side-effect-free bodies.
**Invariant:** endless methods with side effects (`def set_x(x) = (@x = x)`) fail review.
**Probe:** Style/EndlessMethod cop if enabled; manual review for assignment side effects.

## Verdict
Keyword args, explicit call parens, `&&`/`||` in conditions, short focused methods. Learning note: `ruby-style-learning-note.md`.
