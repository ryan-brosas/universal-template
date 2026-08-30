<!-- capsule-v2 -->
# snippet-start-node-reapply — Why must a virtual Start node be re-injected inside the worker?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What breaks when a run's graph depends on request-time-only graph surgery?

## Kind check + DB reload + service reapplication after the worker re-reads the workflow
**Path/Symbol:** `api/core/app/apps/workflow/app_generator.py:WorkflowAppGenerator._ensure_snippet_start_node_in_worker` (:73-90); consumed at `_generate_worker` (:650); alias resolution twin `api/core/workflow/snippet_start.py:get_compatible_start_aliases`.
**Signature:** `_ensure_snippet_start_node_in_worker(*, session: Session, workflow: Workflow) -> Workflow` (staticmethod).
**Data Shape:** Applies only when `workflow.kind_or_standard == "snippet"`; looks up `CustomizedSnippet` by (id==app_id, tenant_id); returns the workflow with a virtual Start node ensured via SnippetGenerateService.

### Decisive source
```python
@staticmethod
def _ensure_snippet_start_node_in_worker(*, session: Session, workflow: Workflow) -> Workflow:
    """Re-apply snippet virtual Start injection after worker reloads workflow from DB."""
    if workflow.kind_or_standard != "snippet":
        return workflow
    from models.snippet import CustomizedSnippet
    from services.snippet_generate_service import SnippetGenerateService

    snippet = session.scalar(
        select(CustomizedSnippet).where(
            CustomizedSnippet.id == workflow.app_id,
            CustomizedSnippet.tenant_id == workflow.tenant_id,
        ))
    if snippet is None:
        return workflow
    return SnippetGenerateService.ensure_start_node_for_worker(workflow, snippet)
```

**Flow:** request thread composes the runnable graph (including virtual Start for snippet-kind apps) → spawns worker → worker RE-READS the workflow row from DB (fresh ORM object without that surgery) → kind gate detects snippet → service re-applies the virtual Start before any Graph.init. Root-input mapping tolerates legacy aliases via `get_compatible_start_aliases(workflow_kind, root_node_id)`.
**Invariant:** Anything computed at REQUEST time that is not persisted must be recomputed in the worker after its own DB load — this hook is the documented seam for exactly that class of drift; non-snippet kinds short-circuit on the cheap string check; missing snippet row degrades to the unmodified workflow (no raise).
**Probe:** `grep -c '_ensure_snippet_start_node_in_worker' core/app/apps/workflow/app_generator.py` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_ensure_snippet_start_node_in_worker snippet virtual start", limit: 10 });
```

## Verdict
Adopt "reapply unpersisted graph surgery after worker reload" as a general rule; keep the kind-gate shape. Adapt what your snippet equivalent is. Omit alias compatibility unless migrating old graphs.
