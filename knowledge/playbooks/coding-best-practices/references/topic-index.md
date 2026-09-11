# Coding best practices — topic index

Route each question to **one leaf**. This index mirrors common "complete guide" outlines (structure, Git, testing, security, AI) but stays agent-native: pointers and gates, not a 700-line tutorial.

## Principles (decision hints, not behavior walls)

| Idea | Where to go | Caveat |
|---|---|---|
| DRY — one source of truth | `code-discipline` | Extract after the second copy, not before the first |
| KISS — simplest working solution | `code-discipline` | Do not ban helpers; remove dead code with gates |
| YAGNI | `code-discipline`, `code-review-and-quality` | Do not block needed prerequisites for "end-to-end" stubs |
| SOLID / separation of concerns | `code-discipline`, language practices | OOP-specific; adapt to your stack |
| Steer outcomes, not behavior | `code-discipline` | Convert repeated failures into CI checks |
| Mechanical enforcement | `practices-to-ci` | Regex/lint/test beats prompting |

## Topic routing

Local reference files: `naming-and-formatting.md`, `documentation-and-readme.md`,
`error-handling-and-resilience.md`, `git-and-collaboration.md`,
`ai-assisted-coding.md`, `performance-and-data-efficiency.md`.

| Topic | Primary leaf skills and gate |
|---|---|
| Naming & formatting | `typescript-coding-practices` (TS style), `typescript-coding-standards` (TS domain), `python-coding-practices` (Python), `javascript-coding-practices` (JS), `go-coding-practices` (Go), `rust-coding-practices` (Rust), `java-coding-practices` (Java), `php-coding-practices` (PHP), `ruby-coding-practices` (Ruby), `kotlin-coding-practices` (Kotlin), `swift-coding-practices` (Swift), `csharp-coding-practices` (C#), `scala-coding-practices` (Scala), project linter |
| Documentation | `markdown-writing-practices`, `google-devdocs-practices` (developer guides), `mailchimp-content-practices` (user-facing copy), `templates/readme.md`, `project-bootstrap` |
| Error handling | `test-generation`, `testing-anti-patterns` |
| Git & collaboration | `git-workflow-and-versioning`, `push-pr` |
| AI-assisted coding | `agent-code-quality-gate`, project `AGENTS.md` |
| Performance & data | profile first; the framework's own source or docs |
| Versioning & releases | `git-workflow-and-versioning`, release tags |
| HTTP/JSON API design | `api-and-interface-design` |
| JSON payload shape | `json-api-practices`, jq/JSON Schema in CI |
| Bash glue scripts | `shell-scripting-practices`, ShellCheck in CI |
| PowerShell modules & tools | `powershell-scripting-practices`, PSScriptAnalyzer in CI |
| SQL queries & schema | `sql-scripting-practices`, sqlfluff in CI |
| Markdown docs | `markdown-writing-practices`, markdownlint in CI |
| Product & marketing copy | `mailchimp-content-practices`, inclusive-language + link-text review in CI |
| Google developer documentation | `google-devdocs-practices`, heading/link review in doc CI |
| HTML/CSS markup | `frontend-markup-practices`; TS/React → the framework's own source or docs |
| MDN doc code examples | `mdn-code-examples-practices`, Prettier MDN config in doc CI |
| Python style & API surface | `python-coding-practices`, Ruff/Black/mypy in CI |
| Django coding style | `django-coding-practices`, pre-commit + manage.py test in CI |
| Symfony coding standards | `symfony-coding-practices`, PHP CS Fixer + phpunit in CI |
| Vue style guide | `vue-coding-practices`, eslint-plugin-vue + vitest in CI |
| Angular style guide | `angular-coding-practices`, angular-eslint + ng test in CI |
| WordPress coding standards | `wordpress-coding-practices`, PHPCS WordPress + plugin/theme tests in CI |
| Drupal coding standards | `drupal-coding-practices`, PHPCS Drupal + PHPStan + ESLint in CI |
| Adobe Commerce / Magento coding standards | `magento-coding-practices`, PHPCS Magento2 + ESLint in CI |
| October CMS developer guidelines | `october-coding-practices`, PSR-2 + naming checklist + composer publish verify |
| JavaScript modules & lint | `javascript-coding-practices`, ESLint/Prettier in CI |
| TypeScript modules & style | `typescript-coding-practices`, `tsc --noEmit` + ESLint in CI |
| Node.js style & npm packaging | `node-coding-practices`, ESLint + npm test in CI |
| JavaScript project setup & workflow | `javascript-project-practices`, lint+test+audit in CI |
| MongoDB schema & data modeling | `mongodb-data-practices`, `$jsonSchema` + index review in CI |
| WCAG 2.1 web accessibility | `wcag-accessibility-practices`, axe + keyboard/SR manual in CI |
| Secure web application coding | `webappsec-coding-practices`, CSRF/HTTPS/upload QA in CI |
| Go style & concurrency | `go-coding-practices`, gofmt/vet/staticcheck in CI |
| Rust style & public API | `rust-coding-practices`, fmt/clippy in CI |
| Java style & public API | `java-coding-practices`, google-java-format/Checkstyle in CI |
| PHP style & typed APIs | `php-coding-practices`, PHP-CS-Fixer/Pint/PHPCS in CI |
| Ruby style & idioms | `ruby-coding-practices`, RuboCop in CI |
| Kotlin style & idioms | `kotlin-coding-practices`, ktlint/detekt in CI |
| Android resources & architecture | `android-coding-practices`, lint + Gradle tests in CI |
| Swift style & API design | `swift-coding-practices`, SwiftLint/SwiftFormat in CI |
| C# / .NET style & API | `csharp-coding-practices`, dotnet format/analyzers in CI |
| Scala style & functional API | `scala-coding-practices`, Scalafmt/Scalafix in CI |
| C++ style & ownership | `cpp-coding-practices`, clang-format/IWYU/cpplint in CI |
| C style & portability | `c-coding-practices`, -Wall/cppcheck in CI |
| Apache httpd C layout | `httpd-c-coding-practices`, GNU indent + httpd build in CI |
| Arduino libraries & sketches | `arduino-coding-practices`, arduino-cli example compile in CI |
| GNU package C layout | `gnu-c-coding-practices`, GNU indent + make check in CI |
| Linux kernel C patches | `linux-kernel-coding-practices`, checkpatch + subsystem build in CI |
| Clojure style & idioms | `clojure-coding-practices`, clj-kondo/cljfmt in CI |
| Common Lisp style & CLOS | `common-lisp-coding-practices`, SBCL/ASDF test in CI |
| D style & Phobos conventions | `d-coding-practices`, dfmt/dub test in CI |
| Dart / Effective Dart | `dart-coding-practices`, dart format/analyze/test in CI |
| Delphi / Object Pascal | `delphi-coding-practices`, IDE formatter + build/test in CI |
| Elm style & TEA modules | `elm-coding-practices`, elm-format/elm-review/test in CI |
| Emacs Lisp style & packages | `emacs-lisp-coding-practices`, checkdoc/package-lint/byte-compile in CI |
| Erlang / OTP style & safety | `erlang-coding-practices`, Elvis/dialyzer/xref/rebar3 in CI |
| F# component design & .NET interop | `fsharp-coding-practices`, Fantomas/dotnet build/C# interop check in CI |
| Fortran / modern F2003+ style | `fortran-coding-practices`, fprettify/FORD/build/test in CI |
| Groovy idioms & public typing | `groovy-coding-practices`, CodeNarc/npm-groovy-lint in CI |
| Haskell layout & totality | `haskell-coding-practices`, stylish-haskell/HLint/cabal in CI |
| Julia BlueStyle & packages | `julia-coding-practices`, JuliaFormatter/Pkg.test in CI |
| Lua modules & locals | `lua-coding-practices`, luacheck/LDoc/busted in CI |
| Nim NEP-1 & stdlib API | `nim-coding-practices`, --styleCheck + nim test in CI |
| Objective-C Cocoa layout | `objc-coding-practices`, clang-format/analyzer in CI |
| Pascal FPC/GPC units | `pascal-coding-practices`, fpc -Wall/fpsonar in CI |
| Perl strict & 3-arg open | `perl-coding-practices`, perlcritic/perltidy/prove in CI |
| R tidyverse pipes & docs | `r-coding-practices`, styler/lintr/testthat in CI |
| Racket modules & contracts | `racket-coding-practices`, DrRacket indent/raco test in CI |
| Solidity layout & Solcurity | `solidity-coding-practices`, forge fmt/test + Slither in CI |
| Visual Basic .NET style | `vb-coding-practices`, Option Strict + dotnet format/build in CI |
| Machine-readable XML formats | `xml-markup-practices`, RELAX NG + xmllint in CI |
| .NET Framework Design & security | `dotnet-coding-practices`, analyzers + CLS in CI; route C#/VB/F# syntax to language skills |
| Elixir style & OTP modules | `elixir-coding-practices`, mix format/credo/test in CI |

## Quality stack (typical implementation loop)

```
coding-best-practices (pick topic)
        ↓
code-discipline (implement scoped)
        ↓
test-driven-development / test-generation / testing-anti-patterns
        ↓
agent-code-quality-gate (before "done")
        ↓
code-review-and-quality (before merge)
        ↓
practices-to-ci (encode new mechanical rules)
        ↓
push-pr (ship with evidence)
```

## Security and CI (parallel tracks)

- **Security surface** → `security-and-hardening` (validate boundaries, secrets, OWASP map).
- **External style catalogs** → the matching `*-coding-practices` leaf or the source library's official documentation.
- **Workflow shape** → `github-actions-engineering`.
- **Catalog repo** → `CONTRIBUTING.md` + `.github/workflows/pr-quality.yml`.
