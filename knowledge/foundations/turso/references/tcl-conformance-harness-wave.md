<!-- capsule-v2 -->
# TCL harness statement-introspection commands — what did the conformance wave add to the bindings, and why does it matter for porters?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** What is the shape of the new TCL C-API surface (statement introspection, bind/connection test commands, empty-result sqlite3 command) and which core contracts do the blessed .sqltest files pin?

## Bindings/tcl expansion + conformance blessing as executable spec
**Path/Symbol:** `bindings/tcl/turso_tcl.c` (+1,064 lines this wave: commits 129b94298 statement introspection + `[db cache]`, 72a1bebae C-API statement/bind/connection test commands, 7a9e29f9c release-build link, 0ce16afd2 `sqlite3` command returns an EMPTY result); conformance side: tester.tcl helpers ported (+306L, harden do_test), all.test statuses updated (71dba7e9a), bless list in `sqlite/conformance/upstream/all.test:344-351` (`json103 pass`, `json502 pass`), new fixture `sqlite/conformance/testing/sqltest/btree-tiny-cell-divider.sqltest` (58L — the min-cell-size divider case as a runnable file); C header contract twin `bindings/c/tests/sqlite3_tests.c` (+30L).
**Signature:** TCL-side commands are thin extern-C wrappers over the SAME `sqlite3_*` C API the compat suite uses — no private core entry points.
**Data Shape:** a `.sqltest` file = ordered `do_execsql_test <id> { SQL } <expected>` records; blessing = flipping its status line to `pass` in all.test once green under the harness runner (`make -C sqlite/conformance run`, Makefile :68-70).

### Decisive source
```text
// all.test:344/:351 — upstream tests adopted as PASSING gates:
//   json103              pass
//   json502              pass
// json502 3.2 (the escape-duality probe):
//   do_execsql_test 3.2 { SELECT '{"abc":123}' ->> 'a\x62c'; } 123
```

**Flow:** port helper → run suite → failures either fix core or stay unblessed; a bless commit asserts the WHOLE file passes (json502 went fully green only after the root-row and precedence fixes). The empty-result rule (`sqlite3 ""` → empty result, not error) mirrors the C-API NULL-stmt contract at the TCL layer.
**Invariant:** conformance status files ARE part of the build's truth: a regression in any blessed file fails CI even though no Rust unit test covers it. For porters: treat blessed .sqltest corpora as the behavioral spec of record, with unit tests as the implementation-level witness.
**Probe:** from repo root: `grep -c 'json103\|json502' sqlite/conformance/upstream/all.test` → 2 both marked pass on their lines; `ls sqlite/conformance/testing/sqltest/btree-tiny-cell-divider.sqltest` exists; `grep -c 'do_execsql_test' sqlite/conformance/upstream/json502.test` → 10. Runner caveat: full sqltest harness needs the built turso binary + uv tooling — recorded BLOCKED-THIS-WINDOW beyond the cargo suites; the pinned grep census + all.test status lines are the deterministic anchors here.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "do_realnum_test", limit: 3 });
```
(harness helpers live in tester.tcl — doc-shaped corpus; if BM25 misses, anchor via search_code pattern 'do_realnum_test' or fall back to the all.test line pins above)

## Verdict
Adopt "blessed corpus = spec" workflow: port helpers, gate on whole-file green, never hand-edit expected values; adapt the TCL layer only if your host language differs; omit the release-link Makefile plumbing outside C-extension packaging. Coverage caveat: sqltest runner blocked this window; census + status-line anchors executed instead.
