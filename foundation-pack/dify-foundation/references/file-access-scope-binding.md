<!-- capsule-v2 -->
# file-access-scope-binding — How does file authorization travel from the request into deep pipeline code?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How is per-request file ownership enforced without threading user objects through every call?

## Context-scoped FileAccessScope bound at generator entry, nullcontext fallback for anonymous
**Path/Symbol:** `api/core/app/apps/base_app_generator.py:BaseAppGenerator._bind_file_access_scope` (:106-127); scope primitives in `api/core/app/file_access/scope.py:bind_file_access_scope` (:87-92), `FileAccessScope.requires_user_ownership` (:37-38).
**Signature:** `_bind_file_access_scope(*, tenant_id, user: Account | EndUser, invoke_from) -> AbstractContextManager[None]`.
**Data Shape:** Scope carries tenant_id/user_id/user_from (ACCOUNT vs END_USER derived from the ORM class)/invoke_from; entered around BOTH `generate()` and `_generate()` bodies.

### Decisive source
```python
@staticmethod
def _bind_file_access_scope(*, tenant_id, user, invoke_from) -> AbstractContextManager[None]:
    """Bind request-scoped file ownership markers for downstream file lookups."""
    user_id = getattr(user, "id", None)
    if not isinstance(user_id, str) or not user_id:
        return nullcontext()          # anonymous/system callers: no markers, no crash
    user_from = UserFrom.ACCOUNT if isinstance(user, Account) else UserFrom.END_USER
    return bind_file_access_scope(FileAccessScope(
        tenant_id=tenant_id, user_id=user_id, user_from=user_from, invoke_from=invoke_from))
```

**Flow:** every entrypoint (`generate`, `_generate`, single-node debug paths) wraps its body in the scope → downstream `file_factory.build_from_*` and access-controller checks read the ambient scope instead of receiving user args → context exits at response completion. Identity kind comes from the CLASS of the user object, not a flag that can drift.
**Invariant:** Missing/empty id degrades to nullcontext rather than binding a half-scope — anonymous paths stay legal but unprivileged; the SAME scope instance must wrap both entity construction (file parsing) and execution so files created mid-run inherit ownership.
**Probe:** `grep -c '_bind_file_access_scope' core/app/apps/base_app_generator.py core/app/apps/workflow/app_generator.py | grep -v ':0'`; direct coverage via `tests/unit_tests/core/app/file_access/` suite (executed green in the layers battery run).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_bind_file_access_scope FileAccessScope tenant user invoke", limit: 10 });
```

## Verdict
Adopt ambient-scope binding with class-derived identity and nullcontext degradation. Adapt what your contextvar carries. Omit the DatabaseFileAccessController internals unless porting Dify's storage ACLs.
