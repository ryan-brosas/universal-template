<!-- capsule-v2 -->
# Private state hardening — files only this user account can read

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you store bearer tokens/session state so other accounts on a shared machine cannot read them, cross-platform?

## harden_directory / harden_file — verify-after-write, extended ACLs dropped
**Path/Symbol:** `linkedin_mcp_server/private_state.py` (`harden_directory` :81, `harden_file` :124, `_verify_posix_owner` :268, `_drop_extended_acl*` :419-476, `_require_acl_support` :216).
**Signature:** `harden_directory(path: Path) -> None`; `harden_file(path: Path) -> None`; modes 0o700 dirs / 0o600 files.
**Data Shape:** POSIX: chmod + owner verification via stat (`is_still_at` identity checks against TOCTOU swaps), then extended-ACL detection (`acl_get_file` via ctypes libc) and dropping any found. Windows: ACL APIs. Neither platform keeps out root/administrator — stated in the module docstring as a boundary, not a goal.

### Decisive source
```text
Defence in depth rather than the only thing standing in the way: it earns
its place when the profile has been redirected, when a parent directory
was created with wider permissions, or when the auth root lives somewhere
outside the profile entirely. Neither platform's mechanism keeps out root
or an administrator, and no file permission ever has.
```
**Flow:** secure_mkdir/write with tight modes → re-stat to confirm no path swap → drop extended ACLs → verify final state; failures wrapped as PrivateStateError naming path+action.
**Invariant:** Harden AFTER creation and VERIFY after hardening — modes set at create time don't cover redirected paths or inherited ACLs; every check re-validates identity (path could have been swapped mid-operation).
**Probe:** `tests/test_private_state.py` (602L) pins mode/owner/ACL outcomes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "harden_directory harden_file acl private state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt harden-then-verify with extended-ACL stripping for credential storage. Adapt to your platforms' ACL APIs. Omit Windows ACE internals (platform detail).
