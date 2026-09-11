<!-- capsule-v2 -->
# Procedures and API — is control flow clear and power used sparingly?

**Source:** NEP-1 §Coding Conventions; getter/setter rules. **Question:** Do procs communicate immutability and return paths without noisy `return`?

## Procedure seam
**Path/Symbol:** procs/funcs in library modules.
**Signature:** `result` assignment; `let` immutability; `proc` before macro/template.
**Data Shape:** method-like procs use `self: Foo`.

### Decisive pattern
```nim
proc repeat(text: string, count: int): string =
  result = ""
  for i in 0..count:
    result.add($i)

proc findUser(id: int): Option[User] =
  if id <= 0:
    return none(User)
  result = some(loadUser(id))

proc fileExists(path: Path): bool =
  discard

proc len*(s: string): int =
  s.len

proc fun(self: Foo, value: int) =
  self.value = value
```

**Flow:** prefer assigning implicit `result` over terminal `return` — use `return` only for early exit or control-flow jumps → declare with `let` when not reassigned; `var` only for mutation → default to `proc`; reach for macro/template/iterator/converter only when compile-time or iteration semantics require it → name method-like first parameter `self` → getters: expose O(1 pure field as `foo`; side-effecting or non-O(1 as `getFoo` → setters: `foo=` or `setFoo` mirroring getter semantics.
**Invariant:** `var` for never-reassigned bindings, macro where `proc` suffices, or `getFoo` for trivial field access fails NEP-1 API review.
**Probe:** immutability scan (`let` vs `var`); return-style review; macro usage grep.

## Power-feature seam
**Flow:** iterators for collection protocols; templates for syntactic sugar with zero runtime cost when justified; document why non-proc construct chosen.
**Invariant:** unexplained macro in hot path without proc alternative fails maintainability review.
**Probe:** `macro`/`template` count vs `proc` in changed module.

## Verdict
result-first procs, let-by-default, proc-first API with consistent getter naming. Learning note: `nim-style-learning-note.md`.
