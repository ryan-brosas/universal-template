# Coding best practices — topic index

Route each question to **one leaf**. This index mirrors common "complete guide" outlines (structure, Git, testing, security, AI) but stays agent-native: pointers and gates, not a 700-line tutorial.

## Principles (decision hints, not behavior walls)

| Idea | Where to go | Caveat |
|---|---|---|
| DRY — one source of truth | `code-discipline` | Extract after the second copy, not before the first |
| KISS — simplest working solution | `code-discipline` | Do not ban helpers; remove dead code with gates |
| YAGNI | `code-discipline`, `code-review-and-quality` | Do not block needed prerequisites for "end-to-end" stubs |
| SOLID / separation of concerns | `code-discipline`, language foundations | OOP-specific; adapt to your stack |
| Steer outcomes, not behavior | `code-discipline` | Convert repeated failures into CI checks |
| Mechanical enforcement | `practices-to-ci` | Regex/lint/test beats prompting |

## Topic files in this skill

| Topic | Reference | Primary leaf skills |
|---|---|---|
| Naming & formatting | `naming-and-formatting.md` | `typescript-coding-practices` (TS style), `typescript-coding-standards` (TS domain), `python-coding-practices` (Python), `javascript-coding-practices` (JS), `go-coding-practices` (Go), `rust-coding-practices` (Rust), `java-coding-practices` (Java), `php-coding-practices` (PHP), `ruby-coding-practices` (Ruby), `kotlin-coding-practices` (Kotlin), `swift-coding-practices` (Swift), `csharp-coding-practices` (C#), `scala-coding-practices` (Scala), project linter |
| Documentation | `documentation-and-readme.md` | `markdown-writing-practices`, `google-devdocs-practices` (developer guides), `mailchimp-content-practices` (user-facing copy), `templates/readme.md`, `project-bootstrap` |
| Error handling | `error-handling-and-resilience.md` | `quality-gate-methodology`, `testing-anti-patterns` |
| Git & collaboration | `git-and-collaboration.md`, `awesome-guidelines` learning notes + git-style capsules | `git-workflow-and-versioning`, `push-pr` |
| AI-assisted coding | `ai-assisted-coding.md` | `agent-code-quality-gate`, project `AGENTS.md` |
| Performance & data | `performance-and-data-efficiency.md` | profile first; stack-specific foundations |
| Versioning & releases | `awesome-guidelines` semver + changelog capsules | `git-workflow-and-versioning`, release tags |
| HTTP/JSON API design | `awesome-guidelines` api-design capsules | `api-design-practices` |
| JSON payload shape | `awesome-guidelines` json-style capsules | `json-api-practices`, jq/JSON Schema in CI |
| Bash glue scripts | `awesome-guidelines` shell-style capsules | `shell-scripting-practices`, ShellCheck in CI |
| PowerShell modules & tools | `awesome-guidelines` powershell-style capsules | `powershell-scripting-practices`, PSScriptAnalyzer in CI |
| SQL queries & schema | `awesome-guidelines` sql-style capsules | `sql-scripting-practices`, sqlfluff in CI |
| Markdown docs | `awesome-guidelines` markdown-style capsules | `markdown-writing-practices`, markdownlint in CI |
| Product & marketing copy | `awesome-guidelines` mailchimp-style capsules | `mailchimp-content-practices`, inclusive-language + link-text review in CI |
| Google developer documentation | `awesome-guidelines` google-devdocs-style capsules | `google-devdocs-practices`, heading/link review in doc CI |
| HTML/CSS markup | `awesome-guidelines` frontend capsules | `frontend-markup-practices`; TS/React → stack capsules in `foundation-pack/` |
| MDN doc code examples | `awesome-guidelines` mdn-style capsules | `mdn-code-examples-practices`, Prettier MDN config in doc CI |
| Python style & API surface | `awesome-guidelines` python-style capsules | `python-coding-practices`, Ruff/Black/mypy in CI |
| Django coding style | `awesome-guidelines` django-style capsules | `django-coding-practices`, pre-commit + manage.py test in CI |
| Symfony coding standards | `awesome-guidelines` symfony-style capsules | `symfony-coding-practices`, PHP CS Fixer + phpunit in CI |
| Vue style guide | `awesome-guidelines` vue-style capsules | `vue-coding-practices`, eslint-plugin-vue + vitest in CI |
| Angular style guide | `awesome-guidelines` angular-style capsules | `angular-coding-practices`, angular-eslint + ng test in CI |
| WordPress coding standards | `awesome-guidelines` wordpress-style capsules | `wordpress-coding-practices`, PHPCS WordPress + plugin/theme tests in CI |
| Drupal coding standards | `awesome-guidelines` drupal-style capsules | `drupal-coding-practices`, PHPCS Drupal + PHPStan + ESLint in CI |
| Adobe Commerce / Magento coding standards | `awesome-guidelines` magento-style capsules | `magento-coding-practices`, PHPCS Magento2 + ESLint in CI |
| October CMS developer guidelines | `awesome-guidelines` october-style capsules | `october-coding-practices`, PSR-2 + naming checklist + composer publish verify |
| JavaScript modules & lint | `awesome-guidelines` javascript-style capsules | `javascript-coding-practices`, ESLint/Prettier in CI |
| TypeScript modules & style | `awesome-guidelines` typescript-style capsules | `typescript-coding-practices`, `tsc --noEmit` + ESLint in CI |
| Node.js style & npm packaging | `awesome-guidelines` node-style capsules | `node-coding-practices`, ESLint + npm test in CI |
| JavaScript project setup & workflow | `awesome-guidelines` js-project capsules | `javascript-project-practices`, lint+test+audit in CI |
| MongoDB schema & data modeling | `awesome-guidelines` mongo-style capsules | `mongodb-data-practices`, `$jsonSchema` + index review in CI |
| WCAG 2.1 web accessibility | `awesome-guidelines` wcag capsules | `wcag-accessibility-practices`, axe + keyboard/SR manual in CI |
| Secure web application coding | `awesome-guidelines` webappsec capsules | `webappsec-coding-practices`, CSRF/HTTPS/upload QA in CI |
| Go style & concurrency | `awesome-guidelines` go-style capsules | `go-coding-practices`, gofmt/vet/staticcheck in CI |
| Rust style & public API | `awesome-guidelines` rust-style capsules | `rust-coding-practices`, fmt/clippy in CI |
| Java style & public API | `awesome-guidelines` java-style capsules | `java-coding-practices`, google-java-format/Checkstyle in CI |
| PHP style & typed APIs | `awesome-guidelines` php-style capsules | `php-coding-practices`, PHP-CS-Fixer/Pint/PHPCS in CI |
| Ruby style & idioms | `awesome-guidelines` ruby-style capsules | `ruby-coding-practices`, RuboCop in CI |
| Kotlin style & idioms | `awesome-guidelines` kotlin-style capsules | `kotlin-coding-practices`, ktlint/detekt in CI |
| Android resources & architecture | `awesome-guidelines` android-style capsules | `android-coding-practices`, lint + Gradle tests in CI |
| Swift style & API design | `awesome-guidelines` swift-style capsules | `swift-coding-practices`, SwiftLint/SwiftFormat in CI |
| C# / .NET style & API | `awesome-guidelines` csharp-style capsules | `csharp-coding-practices`, dotnet format/analyzers in CI |
| Scala style & functional API | `awesome-guidelines` scala-style capsules | `scala-coding-practices`, Scalafmt/Scalafix in CI |
| C++ style & ownership | `awesome-guidelines` cpp-style capsules | `cpp-coding-practices`, clang-format/IWYU/cpplint in CI |
| C style & portability | `awesome-guidelines` c-style capsules | `c-coding-practices`, -Wall/cppcheck in CI |
| Apache httpd C layout | `awesome-guidelines` httpd-style capsules | `httpd-c-coding-practices`, GNU indent + httpd build in CI |
| Arduino libraries & sketches | `awesome-guidelines` arduino-style capsules | `arduino-coding-practices`, arduino-cli example compile in CI |
| GNU package C layout | `awesome-guidelines` gnu-style capsules | `gnu-c-coding-practices`, GNU indent + make check in CI |
| Linux kernel C patches | `awesome-guidelines` linux-kernel-style capsules | `linux-kernel-coding-practices`, checkpatch + subsystem build in CI |
| Clojure style & idioms | `awesome-guidelines` clojure-style capsules | `clojure-coding-practices`, clj-kondo/cljfmt in CI |
| Common Lisp style & CLOS | `awesome-guidelines` lisp-style capsules | `common-lisp-coding-practices`, SBCL/ASDF test in CI |
| D style & Phobos conventions | `awesome-guidelines` d-style capsules | `d-coding-practices`, dfmt/dub test in CI |
| Dart / Effective Dart | `awesome-guidelines` dart-style capsules | `dart-coding-practices`, dart format/analyze/test in CI |
| Delphi / Object Pascal | `awesome-guidelines` delphi-style capsules | `delphi-coding-practices`, IDE formatter + build/test in CI |
| Elm style & TEA modules | `awesome-guidelines` elm-style capsules | `elm-coding-practices`, elm-format/elm-review/test in CI |
| Emacs Lisp style & packages | `awesome-guidelines` emacs-lisp-style capsules | `emacs-lisp-coding-practices`, checkdoc/package-lint/byte-compile in CI |
| Erlang / OTP style & safety | `awesome-guidelines` erlang-style capsules | `erlang-coding-practices`, Elvis/dialyzer/xref/rebar3 in CI |
| F# component design & .NET interop | `awesome-guidelines` fsharp-style capsules | `fsharp-coding-practices`, Fantomas/dotnet build/C# interop check in CI |
| Fortran / modern F2003+ style | `awesome-guidelines` fortran-style capsules | `fortran-coding-practices`, fprettify/FORD/build/test in CI |
| Groovy idioms & public typing | `awesome-guidelines` groovy-style capsules | `groovy-coding-practices`, CodeNarc/npm-groovy-lint in CI |
| Haskell layout & totality | `awesome-guidelines` haskell-style capsules | `haskell-coding-practices`, stylish-haskell/HLint/cabal in CI |
| Julia BlueStyle & packages | `awesome-guidelines` julia-style capsules | `julia-coding-practices`, JuliaFormatter/Pkg.test in CI |
| Lua modules & locals | `awesome-guidelines` lua-style capsules | `lua-coding-practices`, luacheck/LDoc/busted in CI |
| Nim NEP-1 & stdlib API | `awesome-guidelines` nim-style capsules | `nim-coding-practices`, --styleCheck + nim test in CI |
| Objective-C Cocoa layout | `awesome-guidelines` objc-style capsules | `objc-coding-practices`, clang-format/analyzer in CI |
| Pascal FPC/GPC units | `awesome-guidelines` pascal-style capsules | `pascal-coding-practices`, fpc -Wall/fpsonar in CI |
| Perl strict & 3-arg open | `awesome-guidelines` perl-style capsules | `perl-coding-practices`, perlcritic/perltidy/prove in CI |
| R tidyverse pipes & docs | `awesome-guidelines` r-style capsules | `r-coding-practices`, styler/lintr/testthat in CI |
| Racket modules & contracts | `awesome-guidelines` racket-style capsules | `racket-coding-practices`, DrRacket indent/raco test in CI |
| Solidity layout & Solcurity | `awesome-guidelines` solidity-style capsules | `solidity-coding-practices`, forge fmt/test + Slither in CI |
| Visual Basic .NET style | `awesome-guidelines` vb-style capsules | `vb-coding-practices`, Option Strict + dotnet format/build in CI |
| Machine-readable XML formats | `awesome-guidelines` xml-style capsules | `xml-markup-practices`, RELAX NG + xmllint in CI |
| .NET Framework Design & security | `awesome-guidelines` dotnet-style capsules | `dotnet-coding-practices`, analyzers + CLS in CI; route C#/VB/F# syntax to language skills |
| Elixir style & OTP modules | `awesome-guidelines` elixir-style capsules | `elixir-coding-practices`, mix format/credo/test in CI |

## Quality stack (typical implementation loop)

```
coding-best-practices (pick topic)
        ↓
code-discipline (implement scoped)
        ↓
test-driven-development / quality-gate-methodology / testing-anti-patterns
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
- **External style catalogs** → the archived `awesome-guidelines` capsule library (read-only; no new ingestion) and the matching `*-coding-practices` leaf.
- **Workflow shape** → `github-actions-engineering`.
- **Catalog repo** → `CONTRIBUTING.md` + `.github/workflows/pr-quality.yml`.
