<!-- capsule-v2 -->
# Child-process shell-injection surface — why exec(string + input) is RCE and what the checklist is

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** When must user data touch a child process, what contains it?

## Avoid > validate > least-privilege > isolate — in that order
**Path/Symbol:** `sections/security/childprocesses.md` (checklist :7-11, exec example :15-25).
**Signature:** `exec(command)` where command is shell-interpreted text — the danger IS the API.
**Data Shape:** three-line defense checklist: no user input ever; else validate+sanitize; drop privileges via user/group identities; run inside isolation so failures stay contained.

### Decisive source
```javascript
// childprocesses.md :21-24 — the canonical footgun
exec('"/path/to/test file/someScript.sh" --someOption ' + input);
// -> imagine ... '&& rm -rf --no-preserve-root /'
// Node docs: "Never pass unsanitized user input to this function. Any input
// containing shell metacharacters may be used to trigger arbitrary command
// execution." (:29-31)
```

**Flow:** string concatenation hands the WHOLE argument to `/bin/sh` → metacharacters (`&&`, backticks, `$()`) become new commands → remote code execution, data exposure, or destruction. The doc's ladder: eliminate user input first; where unavoidable validate/sanitize before composition; run parent+child under restricted identities; wrap in an isolated environment as the last line.
**Invariant:** the exploit needs no parser confusion — plain shell semantics do all the work. Quoting tricks around the input are NOT a fix while `exec` still routes through a shell; the structural fix (outside this doc's scope but implied by the checklist) is array-argument spawn without shell.
**Probe:** no runner upstream. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'shell metacharacters\|arbitrary command execution' sections/security/childprocesses.md` = 1 (one line carries both phrases) and `grep -cF "require('child_process')"` on the same file = 1. ERRATUM: the original second clause `grep -c 'child_process\.exec' …` ≥ 1 returned 0 at this pin — the doc's require line is `const { exec } = require('child_process');` and its call site is bare `exec(`; no `child_process.exec` member expression exists in the doc.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "arbitrary command execution", "limit": 10}'
# resolves `sections/security/childprocesses.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the ordered checklist as review criteria for any process-spawning code. Adapt to host-language equivalents (subprocess list-args, shlex). Omit nothing — each layer covers a different failure of the previous one.
