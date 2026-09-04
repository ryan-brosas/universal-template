---
name: ruby-coding-practices
description: "Use when authoring or reviewing Ruby, 2-space layout, snake_case/CapitalCase naming, keyword args, call parentheses, class skeleton, explicit namespaces, module_function, and StandardError rescue discipline."
invocation: manual
disable-model-invocation: true
---

# Ruby Coding Practices

Application skill for Ruby style learning (from the archived `awesome-guidelines` style capsules). For Rails/RSpec stack patterns, load stack capsules in `skills/*-foundation`.

## Core Principle

Ruby readability is **RuboCop-community layout plus idiomatic naming and explicit failure**, 2-space files, `?`/`!` suffix rules, keyword args, no exception flow control.

## When to Use / NOT

- Ruby application/library/gem source, RuboCop CI, code review.
- Reviewing naming, methods, class layout, exceptions.

**NOT when:**

- Non-Ruby code.
- Generated files, validate generator config instead.
- Rails-specific cops only, use Rails style guide / foundation when stack is Rails.

## Workflow

1. **Format & layout**, 2-space, spacing, safe nav, blank lines (`ruby-style-formatting-layout.md`).
2. **Naming & files**, snake_case, CapitalCase, `?`/`!`, one class per file (`ruby-style-naming-files.md`).
3. **Methods**, keyword args, parens, `&&`/`||` vs `and`/`or` (`ruby-style-methods-blocks.md`).
4. **Classes & exceptions**, layout, nesting, rescue/raise (`ruby-style-classes-exceptions.md`).
5. **Verify**, RuboCop (project `.rubocop.yml`) + test suite on changed paths.

## Red Flags

- Tabs or 4-space indent
- `is_empty?` / camelCase methods
- `!` method without safe counterpart
- `class Foo::Bar` top-level compact definition
- `@@` class variables
- `rescue ZeroDivisionError` for expected branch
- `rescue Exception`
- Positional default arguments
- `and`/`or` in boolean conditions

## Verification

- `bundle exec rubocop` (or project equivalent) on changed files
- Autoload/Zeitwerk check if namespace/files touched
- Capsule checklist on public API review


## References

- `awesome-guidelines/references/ruby-style-learning-note.md`
- `awesome-guidelines/references/ruby-style-formatting-layout.md`
- `awesome-guidelines/references/ruby-style-naming-files.md`
- `awesome-guidelines/references/ruby-style-methods-blocks.md`
- `awesome-guidelines/references/ruby-style-classes-exceptions.md`
