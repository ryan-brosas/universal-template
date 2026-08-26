<!-- capsule-v2 -->
# Activation transaction — how do you replace a running binary with staged backup/commit/finalize instead of YOLO overwrite?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the state machine for install/update/uninstall of a live executable, including backup lifetime and validation rollback?

## Stage → commit(validate) → finalize(backup gone)
**Path/Symbol:** `src/cli/activation_transaction.c:cbm_activation_transaction_commit` (2135–2219) + suite header tests/test_activation_transaction.c (311–464).
**Signature:** `int cbm_activation_transaction_stage_bytes(target, bytes, len, cbm_activation_transaction_t **out);` → `_commit(tx, validate_fn, ud)` → `_finalize(tx)` → `_close(&tx)`.
**Data Shape:** States STAGED→COMMITTED→FINALIZED. Stage writes a private, owner-ACL'd file beside the target; commit renames into place and keeps the previous binary at a backup path; finalize deletes the backup. Validation callback runs BETWEEN rename and finalization.

### Decisive source
```c
TEST(activation_transaction_commit_keeps_backup_until_finalize) {
    ... stage_bytes(target, "new", ...) ...
    ASSERT_EQ(cbm_activation_transaction_commit(transaction, activation_test_validate, &validation), OK);
    ASSERT_TRUE(activation_test_read(backup_copy, contents));  /* old bytes still present */
    ASSERT_STR_EQ(contents, "old");
    ASSERT_EQ(cbm_activation_transaction_finalize(transaction), OK);
    ASSERT_FALSE(activation_test_exists(backup_copy));
```

**Flow:** stage new bytes (exclusive creation, private ACL; rejects mutating extended ACLs on macOS) → atomically swap target in → run caller's post-commit VALIDATION (e.g., new binary answers --version); failure ⇒ restore previous target from the retained backup → explicit or implicit finalize removes the backup only after success.
**Invariant:** The backup must outlive commit — it is the rollback source until finalize; staging must be exclusive+private to defeat symlink/tmp races.
**Probe:** `tests/test_activation_transaction.c:activation_transaction_commit_keeps_backup_until_finalize`, `activation_transaction_validation_failure_restores_previous_target`, `activation_transaction_explicit_rollback_restores_previous_target`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_activation_transaction_commit", limit: 5 });
```

## Verdict
Adopt stage/validate/finalize for any self-update flow; adapt the ACL work to your platform; omit the Windows reparse-point handling if you only ship POSIX.
