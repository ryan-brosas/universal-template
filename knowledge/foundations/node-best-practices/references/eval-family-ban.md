<!-- capsule-v2 -->
# Eval-family elimination — four global functions that are all the same hole

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Beyond `eval()`, which built-ins compile strings to code, and what replaces each?

## eval / setTimeout(string) / setInterval(string) / new Function — refactor all four
**Path/Symbol:** `sections/security/avoideval.md` (:3 threat surface, :9-15 exploit example).
**Signature:** `eval(str)`, `setTimeout(str)`, `setInterval(str)`, `new Function(...args, body)` — every one parses a string as program text at runtime.
**Data Shape:** exploit primitive: any user-reachable string flowing into any of the four = arbitrary server-side execution with the Node process's full privileges.

### Decisive source
```javascript
// avoideval.md :10-14
const userInput = "require('child_process').spawn('rm', ['-rf', '/'])";
eval(userInput);
```

**Flow:** user input reaching an eval-family call ⇒ "an attacker [can] perform any actions that you can" (:5) — it is RCE, not info leak. The doc's fix is refactoring away from string-form invocation entirely wherever input could reach the parameter.
**Invariant:** teams grep for `eval(` and stop — the doc's point is the OTHER THREE: string-argument timers and `new Function` are the same compiler-with-user-data. Lint coverage exists (`detect-eval-with-expression` in eslint-plugin-security, see lintrules.md :26-29) precisely because manual review keeps missing the non-obvious three. Pair with `childprocess-shell-injection` — same privilege-escalation math, different sink.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'new Function\|setInterval' sections/security/avoideval.md` >= 1 && `grep -c 'eval()' sections/security/avoideval.md` >= 2.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "nodebestpractices", query: "eval new Function setTimeout string code execution", limit: 10 });`

## Verdict
Adopt a blanket ban on eval-family-with-dynamic-input, enforced by lint rule + code review template line. Adapt: pass function references (not strings) to timers; use JSON.parse/lookup tables instead of dynamic compilation. Omit sandboxed-eval exceptions except behind `untrusted-code-sandbox-ladder` rungs.
