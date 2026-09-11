<!-- capsule-v2 -->
# Formatting and layout — is nesting readable without semicolon noise?

**Source:** lua-users LuaStyleGuide §Formatting; LuaRocks §Blocks/Spacing. **Question:** Can reviewers follow `do`/`end` structure at a glance?

## Layout seam
**Path/Symbol:** `.lua` sources and modules.
**Signature:** 2–4 space indent (project-fixed); spaces around operators; no semicolons.
**Data Shape:** one statement per line.

### Decisive pattern
```lua
for i, v in ipairs(items) do
    if is_valid(v) then
        process(v)
    end -- if valid
end -- for items
```

**Flow:** pick 2–4 space indent project-wide (PiL/wiki: 2) — never tabs → space after `--` in comments → space after commas and around operators → one statement per line; no semicolon terminators → on long blocks label closing `end` with `-- if/for` comment → split expressions that would exceed readable line length instead of clever one-liners.
**Invariant:** tabs, semicolon chains, or `--no space` comments fail review.
**Probe:** luacheck whitespace rules; visual indent consistency grep.

## Block seam
**Flow:** single-line blocks only for trivial `then return` / `then break` / short lambdas; expand complex conditions across lines.
**Invariant:** multi-statement one-line `if` fails review.
**Probe:** line-length/complexity spot check.

## Verdict
Consistent space indent, spaced operators, labeled long ends, no semicolons. Learning note: `lua-style-learning-note.md`.
