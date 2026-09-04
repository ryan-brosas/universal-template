<!-- capsule-v2 -->
# Daemon Target.* browser-scope rule — why must browser-level CDP calls carry no session id, and why does `current_tab` have to be resolved server-side?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** A helper sends `Target.getTargetInfo` with no targetId and gets back the *browser* target instead of the attached page — which side owns the fix, and what session-scoping rule makes browser-level calls safe?

## Name-based session strip + server-side identity resolution
**Path/Symbol:** `src/browser_harness/daemon.py`: scope rule in `Daemon.handle` (:721-723), rationale comments (:615-620, :631-634), `current_tab` arm (:631-642), `connection_status` arm (:643-657).

**Signature:** `async def handle(self, req) -> dict`; dispatch line: `sid = None if method.startswith("Target.") else (req.get("session_id") or self.session)`.

**Data Shape:** `current_tab` → `{"targetId", "url", "title"}` or `{"error": "not_attached" | "cdp_disconnected"}`; `connection_status` → `{"target_id", "session_id", "page": {targetId, title, url} | None}` (`None` when the attached target fails the real-page classifier; title/url normalized through `or "(untitled)"` / `or ""`).

### Decisive source
```python
        # Browser-level Target.* calls must not use a session (stale or otherwise).
        # For everything else, explicit session in req wins; else default.
        sid = None if method.startswith("Target.") else (req.get("session_id") or self.session)
```
and, in the `current_tab` arm:
```python
            # Resolve the attached page's target info server-side. Helpers can't
            # send Target.getTargetInfo themselves: daemon strips session_id for
            # any Target.* method (browser-level call), and without a targetId
            # Chrome silently returns the *browser* target.
```

**Flow:** every CDP request passes the name-based gate: any method starting with `Target.` is forced to session-less (browser-level) dispatch because attaching a stale/default page session to a browser-domain command is wrong at the protocol level. Consequence: helpers *cannot* resolve their own identity by calling `Target.getTargetInfo` bare — Chrome answers with the browser target's (empty url/title) info and never raises. The daemon therefore owns identity: `current_tab` resolves `Target.getTargetInfo` **with its tracked `self.target_id`**, returning typed errors instead of guessing (`not_attached` before any wire call; `cdp_disconnected` swallowed-and-typed around the send). Structural corollary: since `sid` is falsy for ALL `Target.*` methods, the stale-session chain-map redirect can never fire on a browser-level call.

**Invariant:** "Silent wrong answer" is worse than an error: the failure mode this design eliminates is a helper reading empty url/title from the browser target and proceeding as if the page were blank. Explicit-session callers keep exact-session semantics (their stale-session error is returned verbatim, never redirected — see test_explicit_stale_session_is_not_redirected :756-776); only implicit-session callers are eligible for recovery redirect.

**Probe:** `tests/unit/test_daemon.py::test_current_tab_meta_passes_attached_target_id` (:301-333, regression for issue #304; asserts the outgoing wire call is exactly `[({"targetId": "page-target-abc"}, None)]`) and `::test_current_tab_meta_returns_not_attached_when_no_target_id` (:336-348; asserts `{"error": "not_attached"}` AND `d.cdp.calls == []`). Cross-checks: `daemon-stale-session-chain-map.md` (redirect semantics), `daemon-named-dedicated-tab.md` (who sets `target_id`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "browser-harness", qualified_name: "browser-harness.src.browser_harness.daemon.Daemon.handle" });
```
Returns :614-764 including both arms and the scope rule (verified live this pass at the post-drift pin; positions shifted +87 from the pre-drift citation).

## Verdict
Adopt the name-prefix session-strip for domain-family dispatch and server-side identity resolution with typed not_attached/cdp_disconnected errors; adapt the `"Target."` prefix set to your protocol's browser-domain families and the error vocabulary to your IPC contract; omit nothing else. Coverage caveat: ambient pytest collection of `test_daemon.py` stays blocked (`cdp_use` missing); both decisive tests were READ and anchor-verified from the pinned checkout instead of executed (lane precedent).
