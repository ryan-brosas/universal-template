---
name: node-coding-practices
description: "Use when authoring or reviewing Node.js, felixge 2-space semicolons, camelCase/===, small early-return functions, top requires, npm/package.json, PORT env, and cross-platform Windows path hygiene."
disable-model-invocation: true
---

# Node.js Coding Practices

Application skill for felixge Node style + Microsoft nodejs-guidelines platform ingest (`awesome-guidelines`). For generic JS modules, load `javascript-coding-practices`. TypeScript Node: add `typescript-coding-standards`.

## Core Principle

Node quality is **small modules with strict style and reproducible npm packaging**, felixge layout habits, top-level requires, no prototype hacks, env-aware servers, cross-platform deps.

## When to Use / NOT

- Node.js apps, npm packages, Express/Fastify servers, CLI tools, native-addon consumers.
- Reviewing `.js` CommonJS/ESM on Node before merge.

**NOT when:**

- Browser-only bundles, `javascript-coding-practices`.
- Pure TypeScript without JS overlap, `typescript-coding-standards` primary.
- MDN documentation examples, `mdn-code-examples-practices`.

## Workflow

1. **Format**, 2-space, semicolons, quotes, braces (`node-style-formatting-layout.md`).
2. **Functions/modules**, size, closures, requires (`node-style-functions-modules.md`).
3. **Naming/conditionals**, ===, predicates, camelCase (`node-style-conditionals-naming.md`).
4. **Platform**, npm, PORT, Windows, native (`node-style-platform-verify.md`).
5. **Verify**, ESLint/EditorConfig + `npm test` + platform notes for native deps.

## Red Flags

- Tabs or mixed tab/space indent
- Trailing whitespace
- Missing semicolons (ASI reliance) on felixge-profile projects
- Double quotes for ordinary strings (felixge profile)
- Allman braces (brace on next line)
- Multi-binding `var a, b, c` on one statement
- snake_case identifiers
- Loose `==` / `!=`
- Complex `if` without named predicate variable
- Deeply nested if/else without early return
- Anonymous nested callback pyramids
- `Array.prototype` / native prototype extension
- Setters with side effects; eval/with
- require/import mid-file
- Hard-coded listen port without env override
- Committed `node_modules`
- Wild `"*"` production dependency versions
- Windows MAX_PATH ignored in deep nested installs
- Global `-g` tools causing version skew
- nodemon in production deployment docs
- Public npm package Windows-only without platform check

## Verification

- ESLint (felixge-aligned or project config) on changed files
- EditorConfig indent/charset/end_of_line
- `npm install && npm test` (or `npm start` smoke)
- Capsule probes on server PORT and require placement
- Native addon: document/build verify on Windows if `node-gyp` in tree


## References

- `awesome-guidelines/references/node-style-learning-note.md`
- `awesome-guidelines/references/node-style-formatting-layout.md`
- `awesome-guidelines/references/node-style-functions-modules.md`
- `awesome-guidelines/references/node-style-conditionals-naming.md`
- `awesome-guidelines/references/node-style-platform-verify.md`

## Related skills

- `javascript-coding-practices`, modern const/let, ES modules
- `powershell-scripting-practices`, Windows shell glue adjacent to Node on Windows
- `shell-scripting-practices`, Unix deploy scripts
