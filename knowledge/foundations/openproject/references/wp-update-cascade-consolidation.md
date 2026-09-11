<!-- capsule-v2 -->
# WP update cascade consolidation — how do ancestor/descendant/reschedule updates collapse into one saved record and one journal entry?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** When one update fans out to related work packages, how does the service guarantee a single DB update (and single journal) per affected work package while still reporting every sub-outcome?

## after_perform cascade + per-id result consolidation
**Path/Symbol:** `app/services/work_packages/update_service.rb:WorkPackages::UpdateService` (`after_perform` :45–55; `consolidated_calls` :177–187; `update_semantic_ids` :112–127).
**Signature:** `initialize(user:, model:, contract_class:, contract_options:, cause_of_rescheduling:)`; `add_dependent!(dependent)` on each child ServiceResult.
**Data Shape:** cascade produces many ServiceResults whose `result`s may be the SAME AR record touched by different services; consolidation groups by `result.id` and folds changes into one master.

### Decisive source
```ruby
# When multiple services change a work package, we still only want one update
# to the database due to: performance / having only one journal entry /
# stale object errors.
def consolidated_calls(service_calls)
  service_calls
    .group_by { |sc| sc.result.id }
    .map do |(_, same_work_package_calls)|
    same_work_package_calls.pop.tap do |master|
      same_work_package_calls.each do |sc|
        master.result.attributes = sc.result.changes.transform_values(&:last)
      end
    end
  end
end

def update_related(work_package, changed_attributes)
  consolidated_calls(update_descendants(work_package) + reschedule_related(work_package, changed_attributes))
    .each { |dependent_call| dependent_call.result.save(validate: false) }
end
```

**Flow:** persist succeeds → `after_perform`: apply subject patterns → update ancestors (their dependents re-parented into this result via `add_dependent!`) → collect descendants-on-project-move + reschedule set (self + former parent when parent changed) → consolidate per id (fold each loser's change values into the master's attributes) → `save(validate: false)` once each → cleanup plane: relations destroyed/time entries+memberships `update_all`-moved/semantic ids re-allocated from `project.reserve_semantic_id_block!` raw-SQL block, then assigned in-memory with `clear_attribute_changes` so representers see fresh ids without reloads.
**Invariant:** one UPDATE + one journal entry per work package regardless of how many services touched it; dependent outcomes stay visible in the parent's `dependent_results` tree; semantic-id reservation bypasses validations by design but must be mirrored into memory.
**Probe:** Deterministic anchors above; behavioral coverage lives in `spec/services/work_packages/update_service_integration_spec.rb` + `update_ancestors_service_spec.rb` (present at pin; not executed — no provisioned DB in lane; recorded caveat). Graph trace evidence: outbound trace of `update_related_work_packages` resolves exactly {consolidated_calls, reschedule_related, update_descendants, add_dependent!, UpdateAncestors.update_ancestors}.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "consolidated calls dependent service results reschedule ancestors descendants single journal", limit: 10, fields: ["signature"] });
// top hit: WorkPackages::UpdateService.consolidated_calls app/services/work_packages/update_service.rb:177-187
```

## Verdict
Adopt group-by-record consolidation before persistence whenever multiple services mutate the same aggregate, plus validate:false for system-computed saves and dependent-result trees for caller visibility. Adapt semantic-id block reservation to host identifier scheme. Omit subject-pattern application if porting without templated types. Coverage: no_recorded_issue @ gen 2026-08-25T20:01:07Z.
