<!-- capsule-v2 -->
# rename_and_delete — tombstone-UUID deletion against racy ping writers

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you delete a row that anonymous internet clients are actively re-creating foreign keys for — without a global lock?

## Check.rename_and_delete
**Path/Symbol:** `hc/api/models.py:rename_and_delete` (:381-406); callers `hc/api/views.py:delete_check` (:520-529), `hc/front/views.py:remove_check` (:868-876); unique_key helper (:430-433).
**Signature:** `rename_and_delete() -> None`; docstring numbers the steps 1-2-3 itself.
**Data Shape:** `code = UUIDField(unique, default=uuid4)` doubles as the ping URL secret; slug is the alternate address under show_slugs. Both must be neutralized before delete; IntegrityError retry is expected and bounded at one.

### Decisive source
```python
# hc/api/models.py — the docstring is the design record
"""Change check's code and slug, then delete the check.

Without changing code and slug first, the check can get pinged during
deletion. The deletion would then fail due to foreign key violation.
This function:
1. Updates check's code and slug to a random value
2. Deletes the check. This step can still fail if a separate process inserts
   a ping between steps 1 and 2.
3. If delete fails, retries it once. This can *still* fail, but is less likely."""

throwaway_uuid = uuid.uuid4()
q = Check.objects.filter(id=self.id)
q.update(code=throwaway_uuid, slug=str(throwaway_uuid))
try:
    q.delete()
except IntegrityError:
    q.delete()
```

**Flow:** One UPDATE swaps both externally-addressable identifiers for a throwaway → any in-flight or subsequent ping by the OLD address 404s instead of inserting → delete. A writer that already passed check-lookup but hasn't INSERTed its Ping when the delete commits still wins once (the FK catches it on the second statement) → exactly-one retry absorbs that window; the residual race is accepted as "less likely" and surfaced as a 500 rather than corrupting state.
**Invariant:** The tombstone swap is unconditional — even if the delete fails the old addresses stay dead, so repeated user retries converge instead of fighting live traffic. Compare HEAD commit 29b5ec2 ("Rewrite to avoid select_for_update"): update_check dropped its lock by adopting save(update_fields)+Check.NotUpdated→404; delete paths keep optimistic discipline because their failure mode is an integrity error they can absorb. API delete_check returns to_dict of the ALREADY-detached instance so the response survives the row's death.
**Probe:** `hc/api/tests/test_check_model.py::test_rename_and_delete_handles_already_deleted_checks` (second stale handle deletes nothing, raises nothing), `hc/front/tests/test_remove_check.py::test_it_works`, `hc/api/tests/test_update_check.py::test_it_handles_concurrent_delete` (get_object_or_404 patched to delete mid-request → 404).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "rename_and_delete throwaway uuid integrity", limit: 10 });
```
Resolves line-exact: rename_and_delete :381-406.

## Verdict
Adopt identifier-tombstoning before delete for any resource addressed by unguessable-in-URL secrets, with a single IntegrityError retry as the honest acknowledgment that you cannot close every window. Adapt to ON DELETE semantics of your store; keep "stale handle must be a no-op". Omit nothing else — the whole primitive is four statements plus the nerve to leave a race open knowingly.
