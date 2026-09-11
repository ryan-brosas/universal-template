<!-- capsule-v2 -->
# Classes and exceptions — are modules, layout, and errors intentional?

**Source:** Ruby Style Guide §Classes & Modules, §Exceptions; Airbnb §Classes, §Exceptions. **Question:** Can constants resolve predictably and failures fail loudly?

## Class layout seam
**Path/Symbol:** domain classes and service modules.
**Signature:** consistent member ordering; explicit nesting; no class variables.
**Data Shape:** `module_function` for stateless utilities.

### Decisive pattern
```ruby
module Utilities
  module_function

  def parse_json(text)
    JSON.parse(text)
  end
end

module Billing
  class InvoiceService
    include Auditable

    SOME_LIMIT = 50

    attr_reader :repository

    def self.build
      new(repository: InvoiceRepository.new)
    end

    def initialize(repository:)
      @repository = repository
    end

    def call(invoice)
      repository.save(invoice)
    end

    private

    def validate!(invoice)
      raise InvalidInvoice, 'empty' if invoice.line_items.empty?
    end
  end
end
```

**Flow:** extend/include/prepend → constants → macros → `def self` → `initialize` → public instance → protected/private → one `include` per line.
**Invariant:** `include Foo, Bar` and `@@shared` class variables fail review; prefer `def self.method` over `class << self` except accessors.
**Probe:** Style/ClassAndModuleChildren (explicit nesting); grep `@@` in diff.

## Namespace seam
```ruby
module Utilities
  class Queue
  end

  class WaitingList
    def initialize
      @queue = Queue.new # resolves Utilities::Queue
    end
  end
end
```

**Flow:** define nested constants with explicit `module` blocks — not `class Utilities::Store` at top level.
**Invariant:** compact `Foo::Bar` class definition at top level is a review reject for new code.
**Probe:** Style/ClassAndModuleChildren; constant lookup specs when refactoring namespaces.

## Exception seam
```ruby
def divide(n, d)
  if d.zero?
    raise DivisionError, 'divide by zero'
  end

  n / d
end

def load_config(path)
  File.read(path)
rescue Errno::ENOENT => e
  raise ConfigMissing, "missing #{path}", e.backtrace
end
```

**Flow:** guard clauses / conditionals for expected branches → rescue specific errors → `raise ErrorClass, 'message'` → never `return` from `ensure` → comment if intentionally swallowing.
**Invariant:** rescue for flow control (`rescue ZeroDivisionError` around `/`), blind `rescue Exception`, and empty rescue bodies without comment fail review.
**Probe:** Lint/SuppressedException, Lint/RescueException cops; tests cover error paths.

## Verdict
Explicit nesting, ordered classes, module_function utilities, StandardError-only rescue with intent. Learning note: `ruby-style-learning-note.md`.
